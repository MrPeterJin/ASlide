#!/usr/bin/env python3
"""
Comprehensive test script for MDS/MDSX file functionality in ASlide.
Similar to VSI testing, this covers all major features.
"""

import os
import sys
import time
import traceback
from PIL import Image
from Aslide.aslide import Slide

def test_basic_properties(slide, filename):
    """Test basic slide properties"""
    print("=== Basic Properties Test ===")
    
    try:
        print(f"File: {os.path.basename(filename)}")
        print(f"Format: {slide.format}")
        print(f"Level count: {slide.level_count}")
        print(f"Dimensions: {slide.dimensions}")
        print(f"Level dimensions: {slide.level_dimensions}")
        print(f"Level downsamples: {slide.level_downsamples}")
        
        # Validate basic properties
        assert slide.level_count > 0, "Level count should be positive"
        assert len(slide.dimensions) == 2, "Dimensions should be (width, height)"
        assert slide.dimensions[0] > 0 and slide.dimensions[1] > 0, "Dimensions should be positive"
        assert len(slide.level_dimensions) == slide.level_count, "Level dimensions count mismatch"
        assert len(slide.level_downsamples) == slide.level_count, "Level downsamples count mismatch"
        
        print("✓ Basic properties test passed")
        return True
        
    except Exception as e:
        print(f"✗ Basic properties test failed: {e}")
        traceback.print_exc()
        return False

def test_properties_dict(slide):
    """Test slide properties dictionary"""
    print("\n=== Properties Dictionary Test ===")
    
    try:
        props = slide.properties
        print("Properties:")
        for key, value in props.items():
            print(f"  {key}: {value}")
        
        # Check for expected properties
        expected_props = ['openslide.mpp-x', 'openslide.mpp-y', 'openslide.vendor']
        for prop in expected_props:
            assert prop in props, f"Missing expected property: {prop}"
        
        # Validate MPP values
        mpp_x = float(props['openslide.mpp-x'])
        mpp_y = float(props['openslide.mpp-y'])
        assert mpp_x > 0 and mpp_y > 0, "MPP values should be positive"
        
        print("✓ Properties dictionary test passed")
        return True
        
    except Exception as e:
        print(f"✗ Properties dictionary test failed: {e}")
        traceback.print_exc()
        return False

def test_region_reading(slide):
    """Test region reading functionality"""
    print("\n=== Region Reading Test ===")
    
    try:
        # Test different region sizes and locations
        test_cases = [
            ((0, 0), 0, (256, 256)),           # Top-left corner
            ((1000, 1000), 0, (512, 512)),    # Middle region
            ((100, 100), 0, (128, 128)),      # Small region
        ]
        
        for i, (location, level, size) in enumerate(test_cases):
            print(f"Test case {i+1}: location={location}, level={level}, size={size}")
            
            region = slide.read_region(location, level, size)
            
            # Validate region
            assert isinstance(region, Image.Image), "Region should be PIL Image"
            assert region.size == size, f"Region size mismatch: expected {size}, got {region.size}"
            assert region.mode in ['RGB', 'RGBA'], f"Unexpected image mode: {region.mode}"
            
            print(f"  ✓ Region {i+1}: {region.size}, mode: {region.mode}")
        
        print("✓ Region reading test passed")
        return True
        
    except Exception as e:
        print(f"✗ Region reading test failed: {e}")
        traceback.print_exc()
        return False

def test_multi_level_reading(slide):
    """Test reading from different levels"""
    print("\n=== Multi-Level Reading Test ===")
    
    try:
        for level in range(min(slide.level_count, 3)):  # Test first 3 levels
            level_dims = slide.level_dimensions[level]
            downsample = slide.level_downsamples[level]
            
            # Read a small region from this level
            region_size = (min(256, level_dims[0]), min(256, level_dims[1]))
            region = slide.read_region((0, 0), level, region_size)
            
            print(f"Level {level}: dims={level_dims}, downsample={downsample:.2f}x, region={region.size}")
            
            assert isinstance(region, Image.Image), f"Level {level} region should be PIL Image"
            assert region.size == region_size, f"Level {level} region size mismatch"
            
        print("✓ Multi-level reading test passed")
        return True
        
    except Exception as e:
        print(f"✗ Multi-level reading test failed: {e}")
        traceback.print_exc()
        return False

def test_thumbnail_generation(slide):
    """Test thumbnail generation"""
    print("\n=== Thumbnail Generation Test ===")
    
    try:
        # Test different thumbnail sizes
        sizes = [(100, 100), (200, 200), (300, 300)]
        
        for size in sizes:
            thumbnail = slide.get_thumbnail(size)
            
            assert isinstance(thumbnail, Image.Image), "Thumbnail should be PIL Image"
            assert thumbnail.size == size, f"Thumbnail size mismatch: expected {size}, got {thumbnail.size}"
            assert thumbnail.mode in ['RGB', 'RGBA'], f"Unexpected thumbnail mode: {thumbnail.mode}"
            
            print(f"  ✓ Thumbnail {size}: mode={thumbnail.mode}")
        
        print("✓ Thumbnail generation test passed")
        return True
        
    except Exception as e:
        print(f"✗ Thumbnail generation test failed: {e}")
        traceback.print_exc()
        return False

def test_best_level_selection(slide):
    """Test best level selection for downsampling"""
    print("\n=== Best Level Selection Test ===")
    
    try:
        # Test different downsample factors
        test_downsamples = [1.0, 2.0, 4.0, 8.0, 16.0]
        
        for downsample in test_downsamples:
            best_level = slide.get_best_level_for_downsample(downsample)
            
            assert 0 <= best_level < slide.level_count, f"Invalid best level: {best_level}"
            
            actual_downsample = slide.level_downsamples[best_level]
            print(f"  Requested: {downsample}x → Level {best_level} ({actual_downsample:.2f}x)")
        
        print("✓ Best level selection test passed")
        return True
        
    except Exception as e:
        print(f"✗ Best level selection test failed: {e}")
        traceback.print_exc()
        return False

def test_associated_images(slide):
    """Test associated images"""
    print("\n=== Associated Images Test ===")
    
    try:
        associated = slide.associated_images
        print(f"Associated images: {list(associated.keys())}")
        
        for name, image in associated.items():
            assert isinstance(image, Image.Image), f"Associated image {name} should be PIL Image"
            print(f"  {name}: {image.size}, mode: {image.mode}")
        
        print("✓ Associated images test passed")
        return True
        
    except Exception as e:
        print(f"✗ Associated images test failed: {e}")
        traceback.print_exc()
        return False

def test_context_manager(filename):
    """Test context manager functionality"""
    print("\n=== Context Manager Test ===")
    
    try:
        # Test with context manager
        with Slide(filename) as slide:
            dims = slide.dimensions
            levels = slide.level_count
            
        # Slide should be closed now
        print(f"✓ Context manager test passed (dims: {dims}, levels: {levels})")
        return True
        
    except Exception as e:
        print(f"✗ Context manager test failed: {e}")
        traceback.print_exc()
        return False

def test_performance(slide):
    """Test performance of various operations"""
    print("\n=== Performance Test ===")
    
    try:
        # Time region reading
        start_time = time.time()
        for i in range(10):
            region = slide.read_region((i*100, i*100), 0, (256, 256))
        region_time = time.time() - start_time
        
        # Time thumbnail generation
        start_time = time.time()
        for i in range(5):
            thumbnail = slide.get_thumbnail((200, 200))
        thumbnail_time = time.time() - start_time
        
        print(f"  Region reading (10x 256x256): {region_time:.3f}s ({region_time/10:.3f}s avg)")
        print(f"  Thumbnail generation (5x 200x200): {thumbnail_time:.3f}s ({thumbnail_time/5:.3f}s avg)")
        
        print("✓ Performance test completed")
        return True
        
    except Exception as e:
        print(f"✗ Performance test failed: {e}")
        traceback.print_exc()
        return False

def run_comprehensive_test(filename):
    """Run comprehensive test on a single file"""
    print(f"\n{'='*60}")
    print(f"COMPREHENSIVE TEST: {os.path.basename(filename)}")
    print(f"{'='*60}")
    
    if not os.path.exists(filename):
        print(f"✗ File not found: {filename}")
        return False
    
    try:
        slide = Slide(filename)
        
        tests = [
            ("Basic Properties", lambda: test_basic_properties(slide, filename)),
            ("Properties Dictionary", lambda: test_properties_dict(slide)),
            ("Region Reading", lambda: test_region_reading(slide)),
            ("Multi-Level Reading", lambda: test_multi_level_reading(slide)),
            ("Thumbnail Generation", lambda: test_thumbnail_generation(slide)),
            ("Best Level Selection", lambda: test_best_level_selection(slide)),
            ("Associated Images", lambda: test_associated_images(slide)),
            ("Performance", lambda: test_performance(slide)),
        ]
        
        passed = 0
        total = len(tests)
        
        for test_name, test_func in tests:
            print(f"\n--- {test_name} ---")
            if test_func():
                passed += 1
        
        slide.close()
        
        # Test context manager separately
        print(f"\n--- Context Manager ---")
        if test_context_manager(filename):
            passed += 1
        total += 1
        
        print(f"\n{'='*60}")
        print(f"SUMMARY: {passed}/{total} tests passed for {os.path.basename(filename)}")
        print(f"{'='*60}")
        
        return passed == total
        
    except Exception as e:
        print(f"✗ Failed to load file: {e}")
        traceback.print_exc()
        return False

def main():
    """Main test function"""
    print("ASlide MDS/MDSX Comprehensive Test Suite")
    print("=" * 60)
    
    # Test files
    test_files = [
        "/jhcnas6/Private/MOTIC/WSI/WCDZZQP/1907469/1.mds",
        "/jhcnas6/Private/MOTIC/WSI/MOTIC_1_180_200710/2.mdsx",
    ]
    
    total_files = 0
    passed_files = 0
    
    for filename in test_files:
        total_files += 1
        if run_comprehensive_test(filename):
            passed_files += 1
    
    print(f"\n{'='*60}")
    print(f"FINAL SUMMARY: {passed_files}/{total_files} files passed all tests")
    print(f"{'='*60}")
    
    if passed_files == total_files:
        print("🎉 All comprehensive tests passed!")
        return 0
    else:
        print("⚠️  Some tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
