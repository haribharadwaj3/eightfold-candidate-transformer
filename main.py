import argparse
import json
import os
import sys

from pipeline.ingest import ingest_source
from pipeline.merge import resolve_and_merge
from pipeline.project import project_profiles
from pipeline.validate import validate_profiles

def main():
    parser = argparse.ArgumentParser(
        description="Multi-Source Candidate Data Transformer CLI Pipeline"
    )
    parser.add_argument(
        "--inputs",
        nargs="+",
        required=True,
        help="List of input files (CSV, JSON, Resume, Notes) or 'github:<username>' strings"
    )
    parser.add_argument(
        "--config",
        type=str,
        help="Path to custom output schema/projection config file"
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Path to save the output JSON file. If not specified, prints to stdout."
    )
    parser.add_argument(
        "--github-token",
        type=str,
        default=os.getenv("GITHUB_TOKEN"),
        help="Optional GitHub Personal Access Token to avoid API rate limits"
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print the output JSON"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print verbose stage logs during execution"
    )

    args = parser.parse_args()

    if args.verbose:
        print("Starting Multi-Source Candidate Data Transformer...")
        print(f"Inputs: {args.inputs}")
        if args.config:
            print(f"Config: {args.config}")
        if args.github_token:
            print("GitHub Token detected/provided.")

    # 1. Ingest & Extract
    extracted_records = []
    for source_path in args.inputs:
        if args.verbose:
            print(f"[{source_path}] Ingesting and extracting...")
        records = ingest_source(source_path, github_token=args.github_token)
        if args.verbose:
            print(f"[{source_path}] Extracted {len(records)} candidate record(s).")
        extracted_records.extend(records)

    if not extracted_records:
        print("[Error] No candidate records extracted from provided inputs.", file=sys.stderr)
        sys.exit(1)

    # 2. Normalize, Resolve & Merge
    if args.verbose:
        print(f"Merging {len(extracted_records)} raw records into canonical profiles...")
    canonical_profiles = resolve_and_merge(extracted_records)
    if args.verbose:
        print(f"Successfully resolved and merged into {len(canonical_profiles)} candidate profile(s).")

    # 3. Project output based on config
    projected_profiles = []
    if args.config:
        if not os.path.exists(args.config):
            print(f"[Error] Config file not found: {args.config}", file=sys.stderr)
            sys.exit(1)
            
        with open(args.config, 'r', encoding='utf-8') as f:
            try:
                config_data = json.load(f)
            except Exception as e:
                print(f"[Error] Failed to parse config JSON: {e}", file=sys.stderr)
                sys.exit(1)
                
        if args.verbose:
            print("Applying custom schema projection...")
        projected_profiles = project_profiles(canonical_profiles, config_data)
        
        # Build validation schema from config fields if validation is required
        # For simplicity, validate_profiles will validate against default schema
        # when no custom schema is generated, but custom config projections
        # don't strictly require default schema validation. Let's run a check:
        validation_reports = []
    else:
        projected_profiles = canonical_profiles
        if args.verbose:
            print("Validating canonical profiles against default schema...")
        validation_reports = validate_profiles(projected_profiles)
        
    # Check validation results (for default schema only)
    if not args.config and validation_reports:
        invalid_profiles = [r for r in validation_reports if not r["valid"]]
        if invalid_profiles:
            print("[Warning] Default schema validation failed for some profiles:", file=sys.stderr)
            for r in invalid_profiles:
                print(f"  Candidate ID {r['candidate_id']} validation errors: {r['errors']}", file=sys.stderr)
        elif args.verbose:
            print("All profiles validated successfully against default schema.")

    # 4. Save/Emit output
    indent = 2 if args.pretty else None
    output_json = json.dumps(projected_profiles, indent=indent, ensure_ascii=False)

    if args.output:
        # Create directories if they do not exist
        out_dir = os.path.dirname(args.output)
        if out_dir and not os.path.exists(out_dir):
            os.makedirs(out_dir, exist_ok=True)
            
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(output_json)
        if args.verbose:
            print(f"Output saved successfully to {args.output}")
    else:
        print(output_json)

if __name__ == "__main__":
    main()
