# v1.9 Commands

Final pipeline from raw evidence:

```powershell
$PY scripts\run_v19_final_pipeline_preview.py --raw-input-dir tests\fixtures\raw_evidence_intake --output-dir outputs\analysis_preview\v19_final_pipeline_raw --emit-all
```

This is raw evidence mode.

Final pipeline from match-pack manifest:

```powershell
$PY scripts\run_v19_final_pipeline_preview.py --match-pack-manifest tests\fixtures\match_packs\match_pack_manifest.csv --output-dir outputs\analysis_preview\v19_final_pipeline_manifest --emit-all
```

This is match pack manifest mode.

Final pipeline from batch config:

```powershell
$PY scripts\run_v19_final_pipeline_preview.py --batch-config tests\fixtures\batch_workbench\lazio_atalanta_batch_config.csv --output-dir outputs\analysis_preview\v19_final_pipeline_batch_config --emit-all
```

This is batch config mode.

Final pipeline from single match mode:

```powershell
$PY scripts\run_v19_final_pipeline_preview.py --single-match-input-dir tests\fixtures\excel_evidence\lazio_atalanta_2026_02_14 --home-team Lazio --away-team Atalanta --competition "Serie A" --season "2025/26" --match-date 2026-02-14 --output-dir outputs\analysis_preview\v19_final_pipeline_single_match --emit-all
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

Final release readiness gate:

```powershell
$PY scripts\run_v19_final_release_readiness_gate_preview.py --final-pipeline-results-json outputs\analysis_preview\v19_final_pipeline_raw\final_pipeline_results.json --output-dir outputs\analysis_preview\v19_final_release_readiness_gate
```

Multi-match Batch OS demo:

```powershell
$PY scripts\run_v19_multi_match_batch_os_demo_preview.py --manifest tests\fixtures\match_packs\match_pack_manifest.csv --output-dir outputs\analysis_preview\v19_multi_match_batch_os_demo --emit-all
```

Raw intake to Batch OS demo:

```powershell
$PY scripts\run_v19_raw_intake_to_batch_os_demo_preview.py --raw-input-dir tests\fixtures\raw_evidence_intake --output-dir outputs\analysis_preview\v19_raw_intake_demo --emit-all
```

Build batch config from match packs:

```powershell
$PY scripts\build_v19_batch_config_from_match_packs_preview.py --manifest tests\fixtures\match_packs\match_pack_manifest.csv --output outputs\analysis_preview\v19_match_pack_scan\auto_batch_config.csv --emit-all
```

Batch health gate:

```powershell
$PY scripts\run_v19_batch_health_gate_preview.py --validation-json outputs\analysis_preview\v19_match_pack_scan\match_pack_validation_results.json --output-dir outputs\analysis_preview\v19_batch_health_gate --emit-all
```

Release stabilization:

```powershell
$PY scripts\run_v19_release_stabilization_preview.py --output-dir outputs\analysis_preview\v19_release_stabilization --emit-all
```
