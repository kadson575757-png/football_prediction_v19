# v1.9 Commands

Final pipeline from raw evidence:

```powershell
$PY scripts\run_v19_final_pipeline_preview.py --raw-input-dir tests\fixtures\raw_evidence_intake --output-dir outputs\analysis_preview\v19_final_pipeline_raw --emit-all
```

Final pipeline from match-pack manifest:

```powershell
$PY scripts\run_v19_final_pipeline_preview.py --match-pack-manifest tests\fixtures\match_packs\match_pack_manifest.csv --output-dir outputs\analysis_preview\v19_final_pipeline_manifest --emit-all
```

Match pack scan:

```powershell
$PY scripts\scan_v19_match_packs_preview.py --manifest tests\fixtures\match_packs\match_pack_manifest.csv --output-dir outputs\analysis_preview\v19_match_pack_scan --emit-all
```

Batch OS:

```powershell
$PY scripts\run_v19_batch_os_preview.py --batch-config tests\fixtures\batch_workbench\lazio_atalanta_batch_config.csv --output-dir outputs\analysis_preview\v19_batch_os --emit-all
```

Completion rerun:

```powershell
$PY scripts\run_v19_batch_completion_rerun_preview.py --base-batch-results-json outputs\analysis_preview\v19_batch_os\batch_workbench\batch_results.json --filled-master-completion-csv outputs\analysis_preview\v19_batch_os\master_completion_template.csv --batch-config tests\fixtures\batch_workbench\lazio_atalanta_batch_config.csv --output-dir outputs\analysis_preview\v19_batch_completion_rerun --emit-all
```

Smoke tests:

```powershell
$PY scripts\run_v19_final_smoke_tests_preview.py --output-dir outputs\analysis_preview\v19_final_smoke_tests --emit-all
```
