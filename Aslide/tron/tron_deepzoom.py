#!/usr/bin/env python3
"""
TRON DeepZoom Generator

TRON 格式天然支持 DeepZoom，因为它本身就是瓦片化存储的。
这个模块提供了高效的 TRON DeepZoom 支持。
"""

import math
from PIL import Image
import io


class TronDeepZoomGenerator:
    """
    TRON 格式的 DeepZoom 生成器
    
    TRON 格式本身就是瓦片化的，所以可以直接映射到 DeepZoom 结构
    """
    
    def __init__(self, tron_slide, tile_size=254, overlap=1, limit_bounds=False):
        """
        初始化 TRON DeepZoom 生成器
        
        Args:
            tron_slide: TronSlide 对象
            tile_size: DeepZoom 瓦片大小 (默认 254)
            overlap: 瓦片重叠像素数 (默认 1)
            limit_bounds: 是否限制边界 (默认 False)
        """
        self._slide = tron_slide
        self._tile_size = tile_size
        self._overlap = overlap
        self._limit_bounds = limit_bounds
        
        # TRON 原生瓦片大小是 1024x1024
        self._native_tile_size = 1024
        
        # 计算 DeepZoom 级别
        self._calculate_levels()
    
    def _calculate_levels(self):
        """计算 DeepZoom 级别信息"""
        # 获取最大尺寸
        max_dimension = max(self._slide.dimensions)
        
        # 计算 DeepZoom 级别数
        # DeepZoom 级别从最小的单瓦片开始，逐级增大
        self._level_count = math.ceil(math.log2(max_dimension / self._tile_size)) + 1
        
        # 计算每个级别的尺寸和瓦片数
        self._level_dimensions = []
        self._level_tiles = []
        
        for level in range(self._level_count):
            # DeepZoom 级别 0 是最小的，级别递增尺寸增大
            # 计算该级别的缩放因子
            scale = 2 ** level
            
            # 计算该级别的像素尺寸
            width = math.ceil(self._slide.dimensions[0] / (2 ** (self._level_count - 1 - level)))
            height = math.ceil(self._slide.dimensions[1] / (2 ** (self._level_count - 1 - level)))
            
            self._level_dimensions.append((width, height))
            
            # 计算该级别的瓦片数
            tiles_x = math.ceil(width / self._tile_size)
            tiles_y = math.ceil(height / self._tile_size)
            self._level_tiles.append((tiles_x, tiles_y))
    
    @property
    def tile_size(self):
        """DeepZoom 瓦片大小"""
        return self._tile_size
    
    @property
    def level_count(self):
        """DeepZoom 级别数"""
        return self._level_count
    
    @property
    def level_tiles(self):
        """每个级别的瓦片数 (tiles_x, tiles_y) 列表"""
        return self._level_tiles
    
    @property
    def level_dimensions(self):
        """每个级别的像素尺寸 (width, height) 列表"""
        return self._level_dimensions
    
    @property
    def tile_count(self):
        """总瓦片数"""
        return sum(tiles_x * tiles_y for tiles_x, tiles_y in self._level_tiles)
    
    def get_dzi(self, format='jpeg'):
        """
        生成 DZI XML 元数据
        
        Args:
            format: 瓦片格式 ('jpeg' 或 'png')
            
        Returns:
            DZI XML 字符串
        """
        width, height = self._slide.dimensions
        
        dzi_xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<Image xmlns="http://schemas.microsoft.com/deepzoom/2008"
       Format="{format}"
       Overlap="{self._overlap}"
       TileSize="{self._tile_size}">
    <Size Width="{width}" Height="{height}"/>
</Image>'''
        
        return dzi_xml
    
    def get_tile(self, level, address):
        """
        获取指定级别和地址的瓦片
        
        Args:
            level: DeepZoom 级别 (0 是最小级别)
            address: 瓦片地址 (col, row) 元组
            
        Returns:
            PIL.Image 瓦片图像
        """
        if level < 0 or level >= self._level_count:
            raise ValueError(f"级别 {level} 超出范围 [0, {self._level_count-1}]")
        
        col, row = address
        tiles_x, tiles_y = self._level_tiles[level]
        
        if col < 0 or col >= tiles_x or row < 0 or row >= tiles_y:
            raise ValueError(f"地址 {address} 超出级别 {level} 的范围")
        
        # 计算对应的 TRON 级别
        # DeepZoom 级别 0 对应最高的 TRON 级别
        tron_level = self._map_deepzoom_to_tron_level(level)
        
        # 计算该级别的尺寸
        level_width, level_height = self._level_dimensions[level]
        
        # 计算瓦片在该级别中的像素位置
        tile_left = col * self._tile_size
        tile_top = row * self._tile_size
        
        # 计算实际瓦片大小（边缘瓦片可能更小）
        tile_width = min(self._tile_size, level_width - tile_left)
        tile_height = min(self._tile_size, level_height - tile_top)
        
        # 如果有重叠，扩展读取区域
        if self._overlap > 0:
            # 扩展读取区域
            read_left = max(0, tile_left - self._overlap)
            read_top = max(0, tile_top - self._overlap)
            read_right = min(level_width, tile_left + tile_width + self._overlap)
            read_bottom = min(level_height, tile_top + tile_height + self._overlap)
            
            read_width = read_right - read_left
            read_height = read_bottom - read_top
        else:
            read_left, read_top = tile_left, tile_top
            read_width, read_height = tile_width, tile_height
        
        # 计算在原始图像中的缩放位置
        scale_factor = 2 ** (self._level_count - 1 - level)
        
        original_left = int(read_left * scale_factor)
        original_top = int(read_top * scale_factor)
        original_width = int(read_width * scale_factor)
        original_height = int(read_height * scale_factor)
        
        # 从 TRON 读取区域
        try:
            # 使用 TRON 的 read_region 方法
            region = self._slide.read_region(
                (original_left, original_top), 
                tron_level, 
                (original_width, original_height)
            )
            
            # 如果读取的区域大小与目标不同，需要缩放
            if region.size != (read_width, read_height):
                region = region.resize((read_width, read_height), Image.LANCZOS)
            
            # 如果有重叠，裁剪到实际瓦片大小
            if self._overlap > 0:
                crop_left = tile_left - read_left
                crop_top = tile_top - read_top
                crop_right = crop_left + tile_width
                crop_bottom = crop_top + tile_height
                
                region = region.crop((crop_left, crop_top, crop_right, crop_bottom))
            
            # 确保瓦片大小正确
            if region.size != (tile_width, tile_height):
                region = region.resize((tile_width, tile_height), Image.LANCZOS)
            
            # 如果瓦片小于标准大小，用白色填充
            if tile_width < self._tile_size or tile_height < self._tile_size:
                padded = Image.new('RGB', (self._tile_size, self._tile_size), 'white')
                padded.paste(region, (0, 0))
                region = padded
            
            return region
            
        except Exception as e:
            # 如果读取失败，返回白色瓦片
            print(f"警告: 读取瓦片 {level}:{address} 失败: {e}")
            return Image.new('RGB', (self._tile_size, self._tile_size), 'white')
    
    def _map_deepzoom_to_tron_level(self, deepzoom_level):
        """
        将 DeepZoom 级别映射到 TRON 级别
        
        Args:
            deepzoom_level: DeepZoom 级别 (0 是最小)
            
        Returns:
            对应的 TRON 级别 (0 是最大)
        """
        # DeepZoom 级别 0 对应最小图像，应该使用最高的 TRON 级别
        # DeepZoom 最高级别对应最大图像，应该使用 TRON 级别 0
        
        # 计算缩放因子
        scale_factor = 2 ** (self._level_count - 1 - deepzoom_level)
        
        # 找到最接近的 TRON 级别
        best_tron_level = 0
        best_diff = float('inf')
        
        for tron_level in range(self._slide.level_count):
            tron_downsample = self._slide.level_downsamples[tron_level]
            diff = abs(tron_downsample - scale_factor)
            
            if diff < best_diff:
                best_diff = diff
                best_tron_level = tron_level
        
        return best_tron_level
    
    def get_tile_coordinates(self, level, address):
        """
        获取瓦片在原始图像中的坐标
        
        Args:
            level: DeepZoom 级别
            address: 瓦片地址 (col, row)
            
        Returns:
            (left, top, width, height) 在原始图像中的坐标
        """
        col, row = address
        
        # 计算缩放因子
        scale_factor = 2 ** (self._level_count - 1 - level)
        
        # 计算瓦片位置
        left = col * self._tile_size * scale_factor
        top = row * self._tile_size * scale_factor
        width = self._tile_size * scale_factor
        height = self._tile_size * scale_factor
        
        # 确保不超出图像边界
        max_width, max_height = self._slide.dimensions
        width = min(width, max_width - left)
        height = min(height, max_height - top)
        
        return (int(left), int(top), int(width), int(height))
