# v2.5 Practical Winner Runner

Use `scripts/run_match_winner_analysis.py` to analyze one match from the winner model pipeline.

The output explains decision class, likely winner or no-clear-winner status, 1X2 probabilities, confidence, source quality, primary reasons, and risk notes.

`WINNER_LEAN` means the model sees a directional edge but not a strong enough full decision. `NO_CLEAR_WINNER` is normal when probabilities are close. Missing xG or odds lowers confidence and adds risk notes, but does not block by itself.

This is winner analysis only. No automatic action, no stake, no ROI.
