# src/data_aggregator.R
# Enhanced aggregation: Adds Vegas lines, weather, and RB stats

library(nflfastR)
library(dplyr)
library(rlang)
library(jsonlite)
library(stringr)

utils::globalVariables(c(
  "game_id", "season", "week", "rush", "rushing_yards", "rush_touchdown", "epa",
  "pass", "passer_player_name", "rusher_player_name", "receiver_player_name",
  "complete_pass", "passing_yards", "pass_touchdown", "yac_epa", "xyac_mean_yardage",
  "home_team", "away_team", "home_score", "away_score", "player_for_agg", "qb_rush_flag",
  "yards_after_catch", "air_yards", "receiving_yards", "xyac_epa", "defteam", "posteam",
  "spread_line", "total_line", "temp", "wind", "roof"  # New globals for added features
))

aggregate_data <- function(config, pbp, output_dir = "data") {
  message("Aggregating data for ", config$target_stat)

  player_field <- config$target_player_field
  play_filter <- config$play_filter
  offense_agg <- config$offense_agg_cols
  team_offense_agg <- config$team_offense_agg_cols
  defense_agg <- config$defense_agg_cols

  pbp <- pbp %>%
    mutate(player_for_agg = coalesce(.data[[player_field]], .data$rusher_player_name))

  # --- Passing stats ---
  message("Aggregating player passing stats...")
  qb_keys <- c("qb_rush_attempts", "qb_rush_yds", "qb_rush_epa")
  offense_pass_agg <- offense_agg[!names(offense_agg) %in% qb_keys]

  player_pass <- pbp %>%
    filter(eval(parse(text = play_filter))) %>%
    filter(!is.na(.data[[player_field]])) %>%
    group_by(.data$game_id, .data$season, .data$week,
             .data[[player_field]], .data$posteam, .data$defteam) %>%
    summarise(
      !!!lapply(names(offense_pass_agg), function(col) {
        expr_text <- offense_pass_agg[[col]]
        if (grepl("\\bmean\\s*\\(", expr_text)) {
          rlang::parse_expr(paste0("coalesce(", expr_text, ", 0)"))
        } else {
          rlang::parse_expr(expr_text)
        }
      }) %>% rlang::set_names(names(offense_pass_agg)),
      is_home = first(.data$posteam == .data$home_team),
      score_diff = mean(
        if_else(.data$posteam == .data$home_team,
                .data$home_score - .data$away_score,
                .data$away_score - .data$home_score),
        na.rm = TRUE
      ),
      # New: Vegas and weather
      expected_spread = mean(.data$spread_line, na.rm = TRUE),
      expected_total = mean(.data$total_line, na.rm = TRUE),
      avg_temp = mean(.data$temp, na.rm = TRUE),
      avg_wind = mean(.data$wind, na.rm = TRUE),
      roof_type = first(.data$roof),
      .groups = "drop"
    )

  # --- QB rushing stats ---
  message("Aggregating QB rushing stats...")
  pbp_rush <- pbp %>%
    filter(.data$rush == 1) %>%
    mutate(qb_rush_flag = if_else(!is.na(.data$rusher_player_name) &
                                    .data$rusher_player_name == .data$player_for_agg, 1L, 0L))

  player_rush <- pbp_rush %>%
    filter(!is.na(.data$player_for_agg)) %>%
    group_by(.data$game_id, .data$season, .data$week,
             .data$player_for_agg, .data$posteam, .data$defteam) %>%
    summarise(
      qb_rush_attempts = sum(.data$qb_rush_flag, na.rm = TRUE),
      qb_rush_yds = sum(if_else(.data$qb_rush_flag == 1L, .data$rushing_yards, 0), na.rm = TRUE),
      qb_rush_tds = sum(if_else(.data$qb_rush_flag == 1L, .data$rush_touchdown, 0), na.rm = TRUE),
      qb_rush_epa = sum(if_else(.data$qb_rush_flag == 1L, .data$epa, 0), na.rm = TRUE),
      .groups = "drop"
    )

  # --- Merge pass + rush ---
  message("Merging player aggregates...")
  player_pass <- player_pass %>% rename(player_name = !!sym(player_field)) %>% distinct()
  player_rush <- player_rush %>% rename(player_name = .data$player_for_agg) %>% distinct()

  player_games <- player_pass %>%
    left_join(player_rush,
              by = c("game_id", "season", "week", "player_name", "posteam", "defteam")) %>%
    mutate(across(where(is.numeric), ~ coalesce(., 0))) %>%
    distinct()

  # --- Write player logs ---
  player_file <- file.path(output_dir, paste0(config$target_stat, "_player_logs.csv"))
  write.csv(player_games, player_file, row.names = FALSE)
  message("Saved player stats to ", player_file)

  # --- Team offense stats ---
  message("Aggregating team offense stats...")
  if ("team_rush_epa" %in% names(team_offense_agg)) {
    team_offense_agg[["team_rush_epa"]] <- "sum(if_else(rush == 1, epa, 0), na.rm = TRUE)"
  }

  team_offense_games <- pbp %>%
    filter(eval(parse(text = play_filter)) | .data$rush == 1) %>%
    group_by(.data$game_id, .data$season, .data$week, .data$posteam, .data$defteam) %>%
    summarise(
      !!!lapply(names(team_offense_agg), function(col) {
        expr_text <- team_offense_agg[[col]]
        if (grepl("\\bmean\\s*\\(", expr_text)) {
          rlang::parse_expr(paste0("coalesce(", expr_text, ", 0)"))
        } else {
          rlang::parse_expr(expr_text)
        }
      }) %>% rlang::set_names(names(team_offense_agg)),
      # New: Vegas and weather (added here too for consistency)
      expected_spread = mean(.data$spread_line, na.rm = TRUE),
      expected_total = mean(.data$total_line, na.rm = TRUE),
      avg_temp = mean(.data$temp, na.rm = TRUE),
      avg_wind = mean(.data$wind, na.rm = TRUE),
      roof_type = first(.data$roof),
      .groups = "drop"
    ) %>%
    mutate(across(where(is.numeric), ~ coalesce(., 0))) %>%
    distinct()

  team_file <- file.path(output_dir, "team_offense_logs.csv")
  write.csv(team_offense_games, team_file, row.names = FALSE)
  message("Saved team offense stats to ", team_file)

  # --- Defense stats ---
  message("Aggregating defense stats...")
  def_games <- pbp %>%
    filter(!is.na(.data$defteam), !is.na(.data$posteam), .data$pass == 1 | .data$rush == 1) %>%
    group_by(.data$game_id, .data$season, .data$week, .data$defteam, .data$posteam) %>%
    summarise(
      !!!lapply(names(defense_agg), function(col) {
        expr_text <- defense_agg[[col]]
        if (grepl("\\bmean\\s*\\(", expr_text)) {
          rlang::parse_expr(paste0("coalesce(", expr_text, ", 0)"))
        } else {
          rlang::parse_expr(expr_text)
        }
      }) %>% rlang::set_names(names(defense_agg)),
      # New: Vegas and weather (for defense perspective)
      expected_spread = mean(.data$spread_line, na.rm = TRUE),
      expected_total = mean(.data$total_line, na.rm = TRUE),
      avg_temp = mean(.data$temp, na.rm = TRUE),
      avg_wind = mean(.data$wind, na.rm = TRUE),
      roof_type = first(.data$roof),
      .groups = "drop"
    ) %>%
    mutate(across(where(is.numeric), ~ coalesce(., 0))) %>%
    distinct()

  def_file <- file.path(output_dir, "defense_logs.csv")
  write.csv(def_games, def_file, row.names = FALSE)
  message("Saved defense stats to ", def_file)

  message("Completed data aggregation for ", config$target_stat)
}