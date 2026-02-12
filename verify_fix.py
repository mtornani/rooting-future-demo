
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from utils.structured_converter import structured_plan_to_markdown
from data_models import StructuredPlan, StructuredSection, DataPoint, Benchmark, Source, SourceType, DataType

def verify_fix():
    print("Verifying fix for structured_converter.py...")
    
    # Create dummy data
    source = Source(type=SourceType.INTERNAL, name="Test Source", reference="Ref")
    benchmark = Benchmark(
        value=100.0, 
        category="Test Category", 
        metric="Test Metric", 
        source=source, 
        year=2024
    )
    
    dp = DataPoint(
        id="test_dp",
        label="Test Data Point",
        category="financial",
        value=120.0,
        unit="EUR",
        data_type=DataType.ESTIMATE,
        source=source,
        benchmark=benchmark,
        confidence=80.0
    )
    
    section = StructuredSection(
        section_id="test_section",
        title="Test Section",
        summary="Summary",
        data_points=[dp]
    )
    
    plan = StructuredPlan(
        plan_id="test_plan",
        club_name="Test Club",
        category="Serie C",
        sections={"test_section": section}
    )
    
    try:
        # This function caused the error before
        markdown_output = structured_plan_to_markdown(plan)
        print("Successfully generated markdown:")
        print(markdown_output["test_section"][:200] + "...") # Print first 200 chars
        print("\nTest PASSED.")
    except AttributeError as e:
        print(f"\nTest FAILED with AttributeError: {e}")
    except Exception as e:
        print(f"\nTest FAILED with Exception: {e}")

if __name__ == "__main__":
    verify_fix()
