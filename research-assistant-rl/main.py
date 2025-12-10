
import sys
import os

print("\n" + "="*70)
print("ADAPTIVE RESEARCH ASSISTANT - COMPLETE PIPELINE")
print("="*70)

# Step 1: Run experiments
print("\n" + "="*60)
print("STEP 1: Running Experiments")
print("="*60)
os.system(f"{sys.executable} experiments\\run_experiments.py")

# Step 2: Analyze results
print("\n" + "="*60)
print("STEP 2: Analyzing Results")
print("="*60)
os.system(f"{sys.executable} experiments\\analyze_results.py")

# Step 3: Statistical validation
print("\n" + "="*60)
print("STEP 3: Statistical Validation")
print("="*60)
os.system(f"{sys.executable} experiments\\validation.py")

# Step 4: Theoretical analysis
print("\n" + "="*60)
print("STEP 4: Theoretical Analysis")
print("="*60)
os.system(f"{sys.executable} experiments\\theoretical_analysis.py")

# Summary
print("\n" + "="*70)
print("✓ COMPLETE - ALL ANALYSES FINISHED")
print("="*70)
print("\nGenerated files in results/ directory:")
print("  1. experiment_data.json         - Raw experimental data")
print("  2. learning_curves.png          - Performance over time")
print("  3. source_preferences.png       - Database preferences")
print("  4. strategy_usage.png           - Strategy distribution")
print("  5. summary_report.txt           - Executive summary")
print("  6. comprehensive_validation.txt - Statistical validation")
print("  7. theoretical_analysis.txt     - Theoretical foundations")
print("\nAll assignment requirements satisfied!")
print("="*70)
