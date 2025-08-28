#!/usr/bin/env python3
"""
Simple MDS/MDSX test: 从level0中间开始连续走五个256格子截图并保存
"""

import os
from Aslide.aslide import Slide

def test_mds_walking(filename):
    """测试从中间开始连续走五个256格子截图并保存"""
    print(f"Testing: {os.path.basename(filename)}")

    try:
        with Slide(filename) as slide:
            print(f"Format: {slide.format}")
            print(f"Dimensions: {slide.dimensions}")
            print(f"Level count: {slide.level_count}")

            # 计算中间位置
            width, height = slide.dimensions
            center_x = width // 2
            center_y = height // 2

            print(f"Center position: ({center_x}, {center_y})")
            print("Walking 5 consecutive 256x256 regions and saving...")

            # 创建输出目录
            base_name = os.path.splitext(os.path.basename(filename))[0]
            output_dir = f"mds_test_output_{base_name}"
            os.makedirs(output_dir, exist_ok=True)

            # 从中间开始连续走五个256格子
            for i in range(5):
                x = center_x + i * 256
                y = center_y

                # 确保不超出边界
                if x + 256 > width:
                    x = width - 256
                if y + 256 > height:
                    y = height - 256

                print(f"  Region {i+1}: ({x}, {y}) -> ", end="")

                region = slide.read_region((x, y), 0, (256, 256))
                print(f"{region.size}, {region.mode} -> ", end="")

                # 验证区域
                assert region.size == (256, 256), f"Wrong size: {region.size}"
                assert region.mode in ['RGB', 'RGBA'], f"Wrong mode: {region.mode}"

                # 保存图像
                output_path = os.path.join(output_dir, f"region_{i+1}_x{x}_y{y}.png")
                region.save(output_path)
                print(f"Saved to {output_path}")

            print(f"✓ All 5 regions read and saved to {output_dir}/")
            return True

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主测试函数"""
    print("MDS/MDSX Walking Test")
    print("=" * 40)
    
    # 测试文件
    test_files = [
        "/jhcnas6/Private/MOTIC/WSI/WCDZZQP/1907469/1.mds",
        "/jhcnas6/Private/MOTIC/WSI/MOTIC_1_180_200710/2.mdsx",
    ]
    
    passed = 0
    total = len(test_files)
    
    for filename in test_files:
        print(f"\nTest {passed + 1}/{total}:")
        if test_mds_walking(filename):
            passed += 1
        print()
    
    print("=" * 40)
    print(f"Result: {passed}/{total} files passed")
    
    if passed == total:
        print("🎉 All tests passed!")
        return 0
    else:
        print("❌ Some tests failed")
        return 1

if __name__ == "__main__":
    exit(main())
