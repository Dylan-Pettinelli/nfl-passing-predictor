#!/usr/bin/env Rscript
# src/update_actuals.R
# Enhanced to calculate Win/Loss column based on Lean vs Actual
# Standardized column name to 'W/L'

library(nflfastR)
library(dplyr)
library(openxlsx)

args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 1 || !grepl("^[0-9]+$", args[1])) {
  stop("Usage: Rscript update_actuals.R <week_number> (e.g., 1 for Week 1)")
}
week <- as.integer(args[1])
season <- 2025
sheet_name <- paste0("Week ", week)
output_file <- "data/passing-prop-predictions-2025.xlsx"

if (!file.exists(output_file)) {
  stop(paste("File", output_file, "does not exist."))
}

# Load existing sheet
existing_df <- tryCatch({
  read.xlsx(output_file, sheet = sheet_name)
}, error = function(e) {
  stop(paste("Sheet", sheet_name, "not found:", e$message))
})

# Fetch PBP data
pbp <- tryCatch({
  load_pbp(seasons = season) %>%
    filter(week == !!week, !is.na(passer_player_name)) %>%
    mutate(player_for_agg = coalesce(passer_player_name, rusher_player_name))
}, error = function(e) {
  warning(paste("Failed to load PBP data:", e$message, "Falling back to manual input."))
  data.frame()
})

# Aggregate passing yards
pbp_pass <- if (nrow(pbp) > 0) {
  pbp %>%
    filter(pass == 1) %>%
    group_by(player_display_name = passer_player_name) %>%
    summarise(passing_yards = sum(passing_yards, na.rm = TRUE), .groups = "drop") %>%
    filter(!is.na(passing_yards))
} else {
  data.frame(player_display_name = character(), passing_yards = numeric())
}

actual_col_idx <- which(colnames(existing_df) == "Actual")
lean_col_idx <- which(colnames(existing_df) == "Lean")
line_col_idx <- which(colnames(existing_df) == "Vegas.Line")
wl_col_idx <- which(colnames(existing_df) == "Win.Loss")  # Standardized to 'W/L'

if (length(actual_col_idx) == 0 || length(lean_col_idx) == 0 || 
    length(line_col_idx) == 0 || length(wl_col_idx) == 0) {
  stop("Required columns not found. Expected: Actual, Lean, Vegas.Line, W/L")
}

updated <- 0
for (i in 1:nrow(existing_df)) {
  player <- existing_df$Player[i]
  
  # Update Actual column if empty
  if (is.na(existing_df[[actual_col_idx]][i]) || existing_df[[actual_col_idx]][i] == "") {
    matched <- pbp_pass %>%
      filter(player_display_name == player)
    
    if (nrow(matched) > 0 && !is.na(matched$passing_yards)) {
      existing_df[[actual_col_idx]][i] <- matched$passing_yards
      cat(sprintf("Auto-filled %s: %d yards\n", player, matched$passing_yards))
      updated <- updated + 1
    } else {
      actual_str <- readline(sprintf("Enter actual yards for %s (or skip): ", player))
      if (nchar(actual_str) > 0) {
        existing_df[[actual_col_idx]][i] <- as.numeric(actual_str)
        updated <- updated + 1
      }
    }
  }
  
  # Calculate W/L if Actual is now filled
  actual_val <- existing_df[[actual_col_idx]][i]
  lean_val <- existing_df[[lean_col_idx]][i]
  line_val <- existing_df[[line_col_idx]][i]
  
  if (!is.na(actual_val) && !is.na(lean_val) && !is.na(line_val)) {
    actual_val <- as.numeric(actual_val)
    line_val <- as.numeric(line_val)
    
    # Determine if prediction was correct
    if (lean_val == "OVER" && actual_val > line_val) {
      existing_df[[wl_col_idx]][i] <- "W"
    } else if (lean_val == "UNDER" && actual_val < line_val) {
      existing_df[[wl_col_idx]][i] <- "W"
    } else if (!is.na(lean_val) && lean_val %in% c("OVER", "UNDER")) {
      existing_df[[wl_col_idx]][i] <- "L"
    }
  }
}

# Save updated sheet back into the workbook
wb <- loadWorkbook(output_file)
if (!sheet_name %in% names(wb)) {
  stop(paste("Sheet", sheet_name, "not found in workbook"))
}
writeData(wb, sheet = sheet_name, x = existing_df, colNames = TRUE)
saveWorkbook(wb, output_file, overwrite = TRUE)

# Calculate and display statistics
wins <- sum(existing_df[[wl_col_idx]] == "W", na.rm = TRUE)
losses <- sum(existing_df[[wl_col_idx]] == "L", na.rm = TRUE)
total_decided <- wins + losses
win_rate <- if (total_decided > 0) (wins / total_decided) * 100 else 0

cat(sprintf("\n=== Week %d Results ===\n", week))
cat(sprintf("Updated %d actual values\n", updated))
cat(sprintf("Record: %d-%d (%.1f%% win rate)\n", wins, losses, win_rate))
cat(sprintf("Pending: %d\n", sum(is.na(existing_df[[wl_col_idx]]))))
cat(sprintf("Saved to: %s\n", output_file))