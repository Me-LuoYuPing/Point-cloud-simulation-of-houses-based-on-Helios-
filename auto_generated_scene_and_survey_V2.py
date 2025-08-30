import numpy as np
import os
import sys
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox, ttk, scrolledtext
from collections import deque
from shapely.geometry import Polygon, Point
from shapely.ops import unary_union
import matplotlib.pyplot as plt
import threading
import math
import shutil
import glob
import random
import re
from pathlib import Path
from datetime import datetime
from typing import List, Tuple, Optional, Dict
import random

# 尝试导入LAS处理库
try:
    import laspy
    HAS_LASPY = True
except ImportError:
    HAS_LASPY = False

# 尝试导入scipy用于ConvexHull
try:
    from scipy.spatial import ConvexHull
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

class AdvancedOBJTriangulator:
    """高级OBJ文件三角化工具"""
    def __init__(self):
        self.vertices = []
        self.normals = []
        self.texcoords = []
        self.faces = []
        self.materials = {}
        self.current_material = "default"
        
    def read_obj_file(self, filepath: str) -> bool:
        """读取OBJ文件"""
        try:
            # 尝试多种编码方式读取文件
            encodings = ['utf-8', 'gbk', 'gb2312', 'latin-1', 'cp1252']
            file_content = None
            
            for encoding in encodings:
                try:
                    with open(filepath, 'r', encoding=encoding) as f:
                        file_content = f.readlines()
                    print(f"成功使用 {encoding} 编码读取OBJ文件")
                    break
                except UnicodeDecodeError:
                    continue
            
            if file_content is None:
                # 如果所有编码都失败，使用二进制模式读取并忽略错误
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    file_content = f.readlines()
                print("使用UTF-8编码（忽略错误）读取OBJ文件")
            
            # 解析文件内容
            for line_num, line in enumerate(file_content, 1):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                parts = line.split()
                if not parts:
                    continue
                
                command = parts[0].lower()
                
                if command == 'v':  # 顶点
                    if len(parts) >= 4:
                        x, y, z = float(parts[1]), float(parts[2]), float(parts[3])
                        self.vertices.append((x, y, z))
                
                elif command == 'vn':  # 法向量
                    if len(parts) >= 4:
                        x, y, z = float(parts[1]), float(parts[2]), float(parts[3])
                        self.normals.append((x, y, z))
                
                elif command == 'vt':  # 纹理坐标
                    if len(parts) >= 3:
                        u, v = float(parts[1]), float(parts[2])
                        self.texcoords.append((u, v))
                
                elif command == 'f':  # 面片
                    if len(parts) >= 4:
                        face = self._parse_face(parts[1:])
                        if face:
                            self.faces.append({
                                'vertices': face,
                                'material': self.current_material
                            })
                
                elif command == 'usemtl':  # 材质
                    if len(parts) >= 2:
                        self.current_material = parts[1]
            
            return True
            
        except Exception as e:
            print(f"读取OBJ文件时出错: {e}")
            return False
    
    def _parse_face(self, face_parts: List[str]) -> Optional[List[dict]]:
        """解析面片定义"""
        face_vertices = []
        
        for part in face_parts:
            # 解析顶点/纹理/法向量索引 (格式: v/vt/vn 或 v//vn 或 v)
            indices = part.split('/')
            
            vertex_data = {}
            
            # 顶点索引
            if indices[0]:
                vertex_data['vertex'] = int(indices[0])
            
            # 纹理坐标索引
            if len(indices) > 1 and indices[1]:
                vertex_data['texcoord'] = int(indices[1])
            
            # 法向量索引
            if len(indices) > 2 and indices[2]:
                vertex_data['normal'] = int(indices[2])
            
            face_vertices.append(vertex_data)
        
        return face_vertices
    
    def triangulate_face_fan(self, face: dict) -> List[dict]:
        """使用扇形三角化"""
        vertices = face['vertices']
        material = face['material']
        
        if len(vertices) <= 3:
            return [face]
        
        triangles = []
        v0 = vertices[0]
        
        for i in range(1, len(vertices) - 1):
            triangle = {
                'vertices': [v0, vertices[i], vertices[i + 1]],
                'material': material
            }
            triangles.append(triangle)
        
        return triangles
    
    def triangulate_all_faces(self, method: str = 'fan'):
        """三角化所有面片"""
        triangulated_faces = []
        
        for i, face in enumerate(self.faces):
            if len(face['vertices']) <= 3:
                triangulated_faces.append(face)
                continue
            
            # 使用扇形三角化
            triangles = self.triangulate_face_fan(face)
            triangulated_faces.extend(triangles)
        
        original_count = len(self.faces)
        self.faces = triangulated_faces
        return original_count, len(triangulated_faces)
    
    def write_obj_file(self, filepath: str) -> bool:
        """写入三角化后的OBJ文件"""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                # 写入头部注释
                f.write("# Triangulated OBJ file\n")
                f.write(f"# Vertices: {len(self.vertices)}\n")
                f.write(f"# Normals: {len(self.normals)}\n")
                f.write(f"# TexCoords: {len(self.texcoords)}\n")
                f.write(f"# Triangles: {len(self.faces)}\n\n")
                
                # 写入顶点
                for i, (x, y, z) in enumerate(self.vertices):
                    f.write(f"v {x:.6f} {y:.6f} {z:.6f}\n")
                
                # 写入法向量
                for i, (x, y, z) in enumerate(self.normals):
                    f.write(f"vn {x:.6f} {y:.6f} {z:.6f}\n")
                
                # 写入纹理坐标
                for i, (u, v) in enumerate(self.texcoords):
                    f.write(f"vt {u:.6f} {v:.6f}\n")
                
                f.write("\n")
                
                # 写入面片
                current_material = None
                for face in self.faces:
                    # 如果材质改变，写入材质声明
                    if face['material'] != current_material:
                        f.write(f"usemtl {face['material']}\n")
                        current_material = face['material']
                    
                    # 写入面片
                    f.write("f")
                    for vertex_data in face['vertices']:
                        f.write(" ")
                        
                        # 顶点索引
                        if 'vertex' in vertex_data:
                            f.write(str(vertex_data['vertex']))
                        
                        # 纹理坐标索引
                        if 'texcoord' in vertex_data:
                            f.write(f"/{vertex_data['texcoord']}")
                        elif 'normal' in vertex_data:
                            f.write("/")
                        
                        # 法向量索引
                        if 'normal' in vertex_data:
                            f.write(f"/{vertex_data['normal']}")
                    
                    f.write("\n")
            
            return True
            
        except Exception as e:
            print(f"写入OBJ文件时出错: {e}")
            return False
    
    def process_file(self, input_file: str, output_file: str = None) -> Tuple[bool, str]:
        """处理OBJ文件"""
        if output_file is None:
            base_name = os.path.splitext(input_file)[0]
            output_file = f"{base_name}_triangulated.obj"
        
        # 读取OBJ文件
        if not self.read_obj_file(input_file):
            return False, output_file
        
        # 三角化面片
        original_count, triangle_count = self.triangulate_all_faces()
        
        # 写入三角化后的文件
        if not self.write_obj_file(output_file):
            return False, output_file
        
        return True, output_file

class HeliosSceneGenerator:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Helios 完整工作流程工具")
        self.root.geometry("800x700")
        
        # 变量
        self.obj_path = tk.StringVar()
        self.output_folder = tk.StringVar()
        self.las_output_folder = tk.StringVar()  # 新增LAS输出文件夹变量
        self.merge_output_folder = tk.StringVar()  # 新增合并输出文件夹变量
        self.step = tk.DoubleVar(value=0.2)
        self.z_height = tk.DoubleVar(value=0.8)
        self.add_ground = tk.BooleanVar(value=False)
        self.max_points = tk.IntVar(value=150)
        self.auto_triangulate = tk.BooleanVar(value=True)  # 自动三角化选项
        self.boundary_distance = tk.DoubleVar(value=0.5)  # 远离边界距离（米）
        self.batch_mode = tk.BooleanVar(value=False)  # 批量处理模式
        self.grid_scan_mode = tk.BooleanVar(value=True)  # 网格扫描模式（默认开启）
        self.scan_direction = tk.StringVar(value="horizontal")  # 扫描方向选择
        self.num_threads = tk.IntVar(value=0)  # 线程数（0表示使用所有可用线程）
        self.enable_multithreading = tk.BooleanVar(value=True)  # 是否启用多线程
        
        # 存储文件路径
        self.survey_file_path = None
        self.output_directory = None
        self.survey_files_list = []  # 批量生成的survey文件列表
        self.batch_obj_files = []  # 批量处理的OBJ文件列表
        self.obj_files_list = []  # 批量模式下的OBJ文件列表
        self.current_boundary_points = None  # 当前处理的边界点
        self.current_scene_path = None  # 当前处理的场景文件路径
        
        self.setup_ui()

    def _get_helios_root(self) -> str:
        """定位仓库根目录，兼容脚本位于根目录或 test/ 子目录的情况。"""
        here = os.path.dirname(os.path.abspath(__file__))
        candidates = [
            here,
            os.path.abspath(os.path.join(here, "..")),
            os.path.abspath(os.path.join(here, "..", "..")),
        ]
        marker_rel = os.path.join("python", "pyhelios", "data", "platforms.xml")
        for c in candidates:
            if os.path.exists(os.path.join(c, marker_rel)):
                return c
        # 回退：优先选择包含 python 目录的路径
        for c in candidates:
            if os.path.isdir(os.path.join(c, "python")):
                return c
        return candidates[0]
    
    def setup_ui(self):
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 文件选择区域
        file_frame = ttk.LabelFrame(main_frame, text="文件选择", padding="5")
        file_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        # 批量模式复选框
        ttk.Checkbutton(file_frame, text="批量处理模式", variable=self.batch_mode, 
                       command=self.toggle_batch_mode).grid(row=0, column=0, columnspan=3, sticky=tk.W, pady=5)
        
        ttk.Label(file_frame, text="OBJ文件:").grid(row=1, column=0, sticky=tk.W)
        ttk.Entry(file_frame, textvariable=self.obj_path, width=50).grid(row=1, column=1, padx=5)
        self.browse_obj_button = ttk.Button(file_frame, text="浏览", command=self.browse_obj_file)
        self.browse_obj_button.grid(row=1, column=2)
        
        ttk.Label(file_frame, text="输出文件夹:").grid(row=2, column=0, sticky=tk.W, pady=5)
        ttk.Entry(file_frame, textvariable=self.output_folder, width=50).grid(row=2, column=1, padx=5, pady=5)
        ttk.Button(file_frame, text="浏览", command=self.browse_output_folder).grid(row=2, column=2, pady=5)
        
        ttk.Label(file_frame, text="LAS输出文件夹:").grid(row=3, column=0, sticky=tk.W, pady=5)
        ttk.Entry(file_frame, textvariable=self.las_output_folder, width=50).grid(row=3, column=1, padx=5, pady=5)
        ttk.Button(file_frame, text="浏览", command=self.browse_las_output_folder).grid(row=3, column=2, pady=5)
        
        ttk.Label(file_frame, text="合并输出文件夹:").grid(row=4, column=0, sticky=tk.W, pady=5)
        ttk.Entry(file_frame, textvariable=self.merge_output_folder, width=50).grid(row=4, column=1, padx=5, pady=5)
        ttk.Button(file_frame, text="浏览", command=self.browse_merge_output_folder).grid(row=4, column=2, pady=5)
        
        # 批量模式下的文件列表显示区域
        self.file_list_frame = ttk.LabelFrame(file_frame, text="已选择的文件", padding="5")
        self.file_list_frame.grid(row=5, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        
        # 创建文件列表框和滚动条
        self.file_listbox = tk.Listbox(self.file_list_frame, height=6, width=70)
        file_scrollbar = ttk.Scrollbar(self.file_list_frame, orient=tk.VERTICAL, command=self.file_listbox.yview)
        self.file_listbox.configure(yscrollcommand=file_scrollbar.set)
        
        self.file_listbox.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5))
        file_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # 文件操作按钮
        file_button_frame = ttk.Frame(self.file_list_frame)
        file_button_frame.grid(row=1, column=0, columnspan=2, pady=5)
        
        ttk.Button(file_button_frame, text="删除选中", command=self.remove_selected_files).grid(row=0, column=0, padx=5)
        ttk.Button(file_button_frame, text="清空列表", command=self.clear_file_list).grid(row=0, column=1, padx=5)
        ttk.Button(file_button_frame, text="查看详情", command=self.show_file_details).grid(row=0, column=2, padx=5)
        
        # 配置文件列表框的列权重
        self.file_list_frame.columnconfigure(0, weight=1)
        
        # 初始时隐藏文件列表区域
        self.file_list_frame.grid_remove()
        
        # 参数设置区域
        param_frame = ttk.LabelFrame(main_frame, text="参数设置", padding="5")
        param_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(param_frame, text="扫描点间距 (米):").grid(row=0, column=0, sticky=tk.W)
        ttk.Entry(param_frame, textvariable=self.step, width=10).grid(row=0, column=1, padx=5)
        
        ttk.Label(param_frame, text="扫描仪高度 (米):").grid(row=1, column=0, sticky=tk.W, pady=5)
        ttk.Entry(param_frame, textvariable=self.z_height, width=10).grid(row=1, column=1, padx=5, pady=5)
        
        # 网格扫描模式选择
        ttk.Checkbutton(param_frame, text="网格扫描模式", variable=self.grid_scan_mode, 
                       command=self.toggle_scan_mode).grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        # 扫描方向选择（仅在网格模式下显示）
        self.scan_direction_frame = ttk.Frame(param_frame)
        self.scan_direction_frame.grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        ttk.Label(self.scan_direction_frame, text="扫描方向:").grid(row=0, column=0, sticky=tk.W)
        self.scan_direction = tk.StringVar(value="horizontal")
        ttk.Radiobutton(self.scan_direction_frame, text="水平", variable=self.scan_direction, value="horizontal").grid(row=0, column=1, padx=5)
        ttk.Radiobutton(self.scan_direction_frame, text="垂直", variable=self.scan_direction, value="vertical").grid(row=0, column=2, padx=5)
        ttk.Radiobutton(self.scan_direction_frame, text="双向", variable=self.scan_direction, value="both").grid(row=0, column=3, padx=5)
        ttk.Radiobutton(self.scan_direction_frame, text="网格", variable=self.scan_direction, value="grid").grid(row=0, column=4, padx=5)
        
        # 最大扫描点数（仅在非网格模式下有效）
        self.max_points_label = ttk.Label(param_frame, text="最大扫描点数:")
        self.max_points_label.grid(row=4, column=0, sticky=tk.W, pady=5)
        self.max_points_entry = ttk.Entry(param_frame, textvariable=self.max_points, width=10)
        self.max_points_entry.grid(row=4, column=1, padx=5, pady=5)
        
        ttk.Label(param_frame, text="远离边界距离 (米):").grid(row=5, column=0, sticky=tk.W, pady=5)
        ttk.Entry(param_frame, textvariable=self.boundary_distance, width=10).grid(row=5, column=1, padx=5, pady=5)
        
        # 多线程设置
        ttk.Checkbutton(param_frame, text="启用多线程加速", variable=self.enable_multithreading).grid(row=6, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        self.thread_frame = ttk.Frame(param_frame)
        self.thread_frame.grid(row=7, column=0, columnspan=2, sticky=tk.W, pady=5)
        ttk.Label(self.thread_frame, text="线程数:").grid(row=0, column=0, sticky=tk.W)
        ttk.Entry(self.thread_frame, textvariable=self.num_threads, width=10).grid(row=0, column=1, padx=5)
        ttk.Label(self.thread_frame, text="(0=自动检测所有核心)").grid(row=0, column=2, sticky=tk.W, padx=5)
        
        ttk.Checkbutton(param_frame, text="添加地面", variable=self.add_ground).grid(row=8, column=0, columnspan=2, sticky=tk.W, pady=5)
        ttk.Checkbutton(param_frame, text="自动三角化OBJ文件", variable=self.auto_triangulate).grid(row=9, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        # 操作按钮区域
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, columnspan=2, pady=10)
        
        # 根据批量模式显示不同按钮
        self.single_button_frame = ttk.Frame(button_frame)
        self.single_button_frame.grid(row=0, column=0, columnspan=4)
        
        ttk.Button(self.single_button_frame, text="生成场景和调查", command=self.generate_scene_and_survey).grid(row=0, column=0, padx=5)
        ttk.Button(self.single_button_frame, text="运行Helios", command=self.run_helios).grid(row=0, column=1, padx=5)
        ttk.Button(self.single_button_frame, text="合并LAS文件", command=self.merge_las_files).grid(row=0, column=2, padx=5)
        
        self.batch_button_frame = ttk.Frame(button_frame)
        
        ttk.Button(self.batch_button_frame, text="导入文件夹", command=self.browse_obj_folder).grid(row=0, column=0, padx=5)
        ttk.Button(self.batch_button_frame, text="选择多个文件", command=self.browse_multiple_obj_files).grid(row=0, column=1, padx=5)
        ttk.Button(self.batch_button_frame, text="批量生成", command=self.batch_generate_scenes_and_surveys).grid(row=0, column=2, padx=5)
        ttk.Button(self.batch_button_frame, text="批量运行", command=self.batch_run_helios).grid(row=0, column=3, padx=5)
        ttk.Button(self.batch_button_frame, text="批量合并", command=self.batch_merge_las_files).grid(row=0, column=4, padx=5)
        
        ttk.Button(button_frame, text="退出", command=self.root.quit).grid(row=1, column=0, columnspan=4, pady=5)
        
        # 日志区域
        log_frame = ttk.LabelFrame(main_frame, text="日志", padding="5")
        log_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        
        self.log_text = tk.Text(log_frame, height=15, width=90)
        scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # 配置网格权重
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(3, weight=1)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        # 配置主窗口权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        
        # 检查依赖库
        self.check_dependencies()
        
        # 初始化扫描模式显示
        self.toggle_scan_mode()
        
        # 显示系统信息
        self.show_system_info()
    
    def toggle_scan_mode(self):
        """切换扫描模式，控制最大点数选项和扫描方向的显示"""
        if self.grid_scan_mode.get():
            # 网格扫描模式：隐藏最大点数选项，显示扫描方向选项
            self.max_points_label.grid_remove()
            self.max_points_entry.grid_remove()
            self.scan_direction_frame.grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=5)
            self.log("切换到网格扫描模式 - 可选择扫描方向")
        else:
            # 传统模式：显示最大点数选项，隐藏扫描方向选项
            self.max_points_label.grid(row=4, column=0, sticky=tk.W, pady=5)
            self.max_points_entry.grid(row=4, column=1, padx=5, pady=5)
            self.scan_direction_frame.grid_remove()
            self.log("切换到传统扫描模式 - 限制最大扫描点数")
    
    def check_dependencies(self):
        """检查并提示依赖库状态"""
        missing_deps = []
        
        if not HAS_LASPY:
            missing_deps.append("laspy (用于LAS文件处理)")
        
        if not HAS_SCIPY:
            missing_deps.append("scipy (用于改进的几何计算)")
        
        if missing_deps:
            self.log("警告: 缺少以下可选依赖库:")
            for dep in missing_deps:
                self.log(f"  - {dep}")
            self.log("部分功能可能受限。建议运行: pip install laspy scipy")
        else:
            self.log("所有依赖库已安装，功能完全可用。")
    
    def show_system_info(self):
        """显示系统信息"""
        import os
        cpu_count = os.cpu_count()
        self.log(f"系统信息: 检测到 {cpu_count} 个CPU核心")
        self.log("多线程模式已启用，可显著提升大型场景的扫描速度")
        if cpu_count and cpu_count >= 4:
            self.log("建议使用多线程模式以获得最佳性能")
        # 自动设置合理的默认线程数（使用CPU核心数-1，留一个核心给系统）
        if cpu_count and cpu_count > 2:
            recommended_threads = max(1, cpu_count - 1)
            self.num_threads.set(recommended_threads)
            self.log(f"推荐线程数: {recommended_threads} (保留1个核心给系统)")
    
    def log(self, message):
        """添加日志消息"""
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)
        self.root.update()
    
    def toggle_batch_mode(self):
        """切换批量处理模式"""
        if self.batch_mode.get():
            # 显示批量操作按钮
            self.single_button_frame.grid_remove()
            self.batch_button_frame.grid(row=0, column=0, columnspan=5)  # 增加列数以容纳新按钮
            # 修改文件浏览按钮功能
            self.browse_obj_button.config(text="导入文件夹", command=self.browse_obj_folder)
            # 显示文件列表区域
            self.file_list_frame.grid(row=5, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
            self.log("切换到批量处理模式 - 可选择文件夹或多个文件")
        else:
            # 显示单个文件操作按钮
            self.batch_button_frame.grid_remove()
            self.single_button_frame.grid(row=0, column=0, columnspan=4)
            # 恢复文件浏览按钮功能
            self.browse_obj_button.config(text="浏览", command=self.browse_obj_file)
            # 隐藏文件列表区域
            self.file_list_frame.grid_remove()
            self.log("切换到单文件处理模式")

    def browse_obj_file(self):
        """浏览OBJ文件"""
        filename = filedialog.askopenfilename(
            title="选择OBJ文件",
            filetypes=[("OBJ files", "*.obj"), ("All files", "*.*")]
        )
        if filename:
            self.obj_path.set(filename)
            # 自动设置输出文件夹
            base_name = os.path.splitext(os.path.basename(filename))[0]
            output_dir = os.path.join(os.path.dirname(filename), base_name)
            self.output_folder.set(output_dir)
            self.log(f"选择了OBJ文件: {filename}")

    def browse_obj_folder(self):
        """浏览并选择包含OBJ文件的文件夹"""
        folder = filedialog.askdirectory(title="选择包含OBJ文件的文件夹")
        if folder:
            # 搜索文件夹中的所有OBJ文件
            obj_files = glob.glob(os.path.join(folder, "*.obj"))
            if obj_files:
                self.obj_files_list = obj_files
                # 更新文件列表显示
                self.update_file_list_display()
                
                self.log(f"从文件夹导入了 {len(obj_files)} 个OBJ文件:")
                for i, obj_file in enumerate(obj_files[:5]):  # 只显示前5个
                    self.log(f"  {i+1}. {os.path.basename(obj_file)}")
                if len(obj_files) > 5:
                    self.log(f"  ... 还有 {len(obj_files)-5} 个文件")
            else:
                self.obj_files_list = []
                self.update_file_list_display()
                self.log(f"在文件夹 {folder} 中未找到OBJ文件")
                messagebox.showwarning("警告", "选择的文件夹中没有找到OBJ文件")
    
    def browse_output_folder(self):
        """浏览输出文件夹"""
        folder = filedialog.askdirectory(title="选择输出文件夹")
        if folder:
            self.output_folder.set(folder)
            self.log(f"设置输出文件夹: {folder}")
            # 同时设置output_directory用于其他方法
            self.output_directory = folder
    
    def browse_las_output_folder(self):
        """浏览LAS输出文件夹"""
        folder = filedialog.askdirectory(title="选择LAS文件输出文件夹")
        if folder:
            self.las_output_folder.set(folder)
            self.log(f"设置LAS输出文件夹: {folder}")
    
    def browse_merge_output_folder(self):
        """浏览合并输出文件夹"""
        folder = filedialog.askdirectory(title="选择合并文件输出文件夹")
        if folder:
            self.merge_output_folder.set(folder)
            self.log(f"设置合并输出文件夹: {folder}")
    
    def browse_multiple_obj_files(self):
        """选择多个OBJ文件"""
        filenames = filedialog.askopenfilenames(
            title="选择多个OBJ文件",
            filetypes=[("OBJ files", "*.obj"), ("All files", "*.*")]
        )
        if filenames:
            # 将新选择的文件添加到列表中（避免重复）
            new_files = []
            for filename in filenames:
                if filename not in self.obj_files_list:
                    self.obj_files_list.append(filename)
                    new_files.append(filename)
            
            # 更新UI显示
            self.update_file_list_display()
            
            if new_files:
                self.log(f"添加了 {len(new_files)} 个新的OBJ文件:")
                for i, obj_file in enumerate(new_files[:5]):  # 只显示前5个
                    self.log(f"  {i+1}. {os.path.basename(obj_file)}")
                if len(new_files) > 5:
                    self.log(f"  ... 还有 {len(new_files)-5} 个文件")
                self.log(f"总共选择了 {len(self.obj_files_list)} 个OBJ文件")
            else:
                self.log("选择的文件都已存在于列表中")
    
    def update_file_list_display(self):
        """更新文件列表显示"""
        # 清空当前列表
        self.file_listbox.delete(0, tk.END)
        
        # 添加所有文件到列表框
        for obj_file in self.obj_files_list:
            filename = os.path.basename(obj_file)
            self.file_listbox.insert(tk.END, filename)
        
        # 更新路径显示
        if self.obj_files_list:
            self.obj_path.set(f"已选择 {len(self.obj_files_list)} 个OBJ文件")
        else:
            self.obj_path.set("")
    
    def remove_selected_files(self):
        """删除选中的文件"""
        selected_indices = list(self.file_listbox.curselection())
        if not selected_indices:
            messagebox.showwarning("提示", "请先选择要删除的文件")
            return
        
        # 从后往前删除，避免索引变化问题
        selected_indices.reverse()
        removed_files = []
        
        for index in selected_indices:
            if 0 <= index < len(self.obj_files_list):
                removed_file = self.obj_files_list.pop(index)
                removed_files.append(os.path.basename(removed_file))
        
        # 更新显示
        self.update_file_list_display()
        
        if removed_files:
            self.log(f"删除了 {len(removed_files)} 个文件: {', '.join(removed_files)}")
            if self.obj_files_list:
                self.log(f"剩余 {len(self.obj_files_list)} 个文件")
            else:
                self.log("文件列表已清空")
    
    def clear_file_list(self):
        """清空文件列表"""
        if not self.obj_files_list:
            messagebox.showinfo("提示", "文件列表已经是空的")
            return
        
        count = len(self.obj_files_list)
        result = messagebox.askyesno("确认", f"确定要清空所有 {count} 个文件吗？")
        if result:
            self.obj_files_list.clear()
            self.update_file_list_display()
            self.log(f"已清空文件列表（原有 {count} 个文件）")
    
    def show_file_details(self):
        """显示文件详情"""
        if not self.obj_files_list:
            messagebox.showinfo("提示", "没有选择任何文件")
            return
        
        # 创建详情窗口
        detail_window = tk.Toplevel(self.root)
        detail_window.title("文件详情")
        detail_window.geometry("800x500")
        detail_window.transient(self.root)
        detail_window.grab_set()
        
        # 创建文本框和滚动条
        detail_frame = ttk.Frame(detail_window, padding="10")
        detail_frame.pack(fill=tk.BOTH, expand=True)
        
        detail_text = scrolledtext.ScrolledText(detail_frame, wrap=tk.WORD, width=90, height=25)
        detail_text.pack(fill=tk.BOTH, expand=True)
        
        # 显示文件信息
        detail_text.insert(tk.END, f"已选择文件详情 (共 {len(self.obj_files_list)} 个文件)\n")
        detail_text.insert(tk.END, "=" * 80 + "\n\n")
        
        total_size = 0
        for i, obj_file in enumerate(self.obj_files_list, 1):
            try:
                file_size = os.path.getsize(obj_file)
                total_size += file_size
                size_str = self.format_file_size(file_size)
                
                detail_text.insert(tk.END, f"{i:3d}. {os.path.basename(obj_file)}\n")
                detail_text.insert(tk.END, f"     路径: {obj_file}\n")
                detail_text.insert(tk.END, f"     大小: {size_str}\n")
                
                # 获取文件修改时间
                mtime = os.path.getmtime(obj_file)
                mtime_str = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
                detail_text.insert(tk.END, f"     修改时间: {mtime_str}\n\n")
                
            except Exception as e:
                detail_text.insert(tk.END, f"{i:3d}. {os.path.basename(obj_file)} (读取失败: {e})\n\n")
        
        detail_text.insert(tk.END, f"总大小: {self.format_file_size(total_size)}\n")
        
        # 添加关闭按钮
        close_button = ttk.Button(detail_frame, text="关闭", command=detail_window.destroy)
        close_button.pack(pady=10)
        
        # 设置文本为只读
        detail_text.config(state=tk.DISABLED)
    
    def batch_generate_scenes_and_surveys(self):
        """批量生成场景和调查文件"""
        if not self.obj_files_list:
            messagebox.showerror("错误", "请先选择包含OBJ文件的文件夹")
            return
        
        if not self.output_folder.get():
            messagebox.showerror("错误", "请先选择输出文件夹")
            return
        
        self.log("开始批量生成场景和调查文件...")
        success_count = 0
        failed_count = 0
        
        for obj_file in self.obj_files_list:
            try:
                # 获取文件名（不含扩展名）
                base_name = os.path.splitext(os.path.basename(obj_file))[0]
                
                # 为每个OBJ文件创建独立的输出文件夹
                obj_output_dir = os.path.join(self.output_folder.get(), base_name)
                os.makedirs(obj_output_dir, exist_ok=True)
                
                self.log(f"处理文件: {base_name}")
                
                # 临时设置当前处理的文件路径
                original_obj_path = self.obj_path.get()
                original_output_dir = self.output_directory
                
                self.obj_path.set(obj_file)
                self.output_directory = obj_output_dir
                
                # 调用单文件处理方法
                success = self._generate_single_scene_and_survey()
                
                if success:
                    success_count += 1
                    self.log(f"  ✓ {base_name} 处理成功")
                else:
                    failed_count += 1
                    self.log(f"  ✗ {base_name} 处理失败")
                
                # 恢复原始路径
                self.obj_path.set(original_obj_path)
                self.output_directory = original_output_dir
                
            except Exception as e:
                failed_count += 1
                self.log(f"  ✗ {base_name} 处理失败: {str(e)}")
        
        self.log(f"批量生成完成: 成功 {success_count} 个，失败 {failed_count} 个")
        messagebox.showinfo("完成", f"批量生成完成\n成功: {success_count} 个\n失败: {failed_count} 个")

    def _generate_single_scene_and_survey(self):
        """生成单个场景和调查文件（内部方法）"""
        try:
            # 这里复制原有的generate_scene_and_survey方法的主要逻辑
            obj_path = self.obj_path.get()
            
            if not obj_path or not os.path.exists(obj_path):
                self.log("请选择有效的OBJ文件")
                return False
            
            # 三角化处理
            if self.auto_triangulate.get():
                obj_path = self.triangulate_obj_file(obj_path)
                if not obj_path:
                    return False
            
            # 生成场景文件
            scene_success = self.generate_scene_file(obj_path)
            if not scene_success:
                return False
            
            # 生成调查文件
            survey_success = self.generate_survey_file()
            if not survey_success:
                return False
            
            return True
            
        except Exception as e:
            self.log(f"生成场景和调查失败: {str(e)}")
            return False

    def generate_scene_file(self, obj_path):
        """生成场景文件"""
        try:
            # 解析OBJ文件
            min_xyz, max_xyz, vertices, faces = self.parse_obj_bbox(obj_path)
            self.log(f"OBJ包围盒 min: {min_xyz}, max: {max_xyz}")
            self.log(f"房屋高度: {max_xyz[2] - min_xyz[2]:.2f} 米")
            
            # 提取房屋轮廓
            boundary_points = self.extract_floor_plan(vertices, faces)
            self.log(f"房屋轮廓包含 {len(boundary_points)-1} 个边界点")
            
            # 生成文件路径
            base_name = os.path.splitext(os.path.basename(obj_path))[0]
            scene_xml_path = os.path.join(self.output_directory, f"{base_name}_scene.xml")
            
            # 生成场景文件
            self.generate_scene_xml(obj_path, scene_xml_path, add_ground=self.add_ground.get())
            
            # 保存边界点和场景路径供生成调查文件使用
            self.current_boundary_points = boundary_points
            self.current_scene_path = scene_xml_path
            
            return True
            
        except Exception as e:
            self.log(f"生成场景文件失败: {str(e)}")
            return False

    def generate_survey_file(self):
        """生成调查文件"""
        try:
            if not hasattr(self, 'current_boundary_points') or not hasattr(self, 'current_scene_path'):
                self.log("请先生成场景文件")
                return False
            
            # 获取参数
            step = self.step.get()
            z_height = self.z_height.get()
            max_points = self.max_points.get()
            boundary_distance = self.boundary_distance.get()
            
            # 优化扫描路径
            scan_path = self.optimize_scan_path(
                self.current_boundary_points, 
                step=step, 
                z_height=z_height, 
                max_points=max_points, 
                boundary_distance=boundary_distance
            )
            
            # 生成调查文件路径
            base_name = os.path.splitext(os.path.basename(self.current_scene_path))[0].replace('_scene', '')
            survey_xml_path = os.path.join(self.output_directory, f"{base_name}_survey.xml")
            visualization_path = os.path.join(self.output_directory, f"{base_name}_path.png")
            
            # 生成优化的survey文件
            las_output_root = self.las_output_folder.get() if self.las_output_folder.get() else None
            self.generate_optimized_survey_xml(self.current_scene_path, scan_path, survey_xml_path, z_height=z_height, las_output_root=las_output_root)
            
            # 可视化扫描路径
            self.visualize_scan_path(self.current_boundary_points, scan_path, visualization_path, boundary_distance)
            
            self.log(f"Survey文件: {survey_xml_path}")
            self.log(f"扫描点数量: {len(scan_path)} 个")
            self.log(f"边界距离: {boundary_distance:.2f} 米")
            
            return True
            
        except Exception as e:
            self.log(f"生成调查文件失败: {str(e)}")
            return False

    def batch_run_helios(self):
        """批量运行Helios扫描"""
        if not self.output_folder.get():
            messagebox.showerror("错误", "请先选择输出文件夹")
            return
        
        self.log("搜索批量生成的survey文件...")
        
        # 搜索所有子文件夹中的survey文件
        survey_files = []
        output_root = self.output_folder.get()
        
        # 遍历输出文件夹下的所有子目录
        for item in os.listdir(output_root):
            item_path = os.path.join(output_root, item)
            if os.path.isdir(item_path):
                # 在每个子文件夹中查找survey文件
                for file in os.listdir(item_path):
                    if file.endswith("_survey.xml"):
                        survey_file_path = os.path.join(item_path, file)
                        survey_files.append(survey_file_path)
                        self.log(f"找到survey文件: {survey_file_path}")
        
        if not survey_files:
            self.log("详细搜索结果:")
            # 打印详细的文件夹结构用于调试
            for item in os.listdir(output_root):
                item_path = os.path.join(output_root, item)
                if os.path.isdir(item_path):
                    self.log(f"文件夹: {item}")
                    for file in os.listdir(item_path):
                        self.log(f"  - {file}")
            
            messagebox.showerror("错误", "在输出文件夹中未找到survey文件\n请先执行批量生成操作")
            return
        
        self.log(f"找到 {len(survey_files)} 个survey文件，开始批量运行Helios...")
        
        success_count = 0
        failed_count = 0
        
        for survey_file in survey_files:
            try:
                folder_name = os.path.basename(os.path.dirname(survey_file))
                survey_name = os.path.basename(survey_file)
                self.log(f"运行扫描: {folder_name}/{survey_name}")
                
                # 运行Helios
                success = self._run_single_helios(survey_file)
                
                if success:
                    success_count += 1
                    self.log(f"  ✓ {folder_name} 扫描完成")
                else:
                    failed_count += 1
                    self.log(f"  ✗ {folder_name} 扫描失败")
                
            except Exception as e:
                failed_count += 1
                folder_name = os.path.basename(os.path.dirname(survey_file))
                self.log(f"  ✗ {folder_name} 扫描失败: {str(e)}")
        
        self.log(f"批量扫描完成: 成功 {success_count} 个，失败 {failed_count} 个")
        messagebox.showinfo("完成", f"批量扫描完成\n成功: {success_count} 个\n失败: {failed_count} 个")

    def _run_single_helios(self, survey_file):
        """运行单个Helios扫描（内部方法）"""
        try:
            # 构建基础命令
            cmd = f'helios "{survey_file}" --lasOutput'
            
            # 添加多线程支持
            if self.enable_multithreading.get():
                num_threads = self.num_threads.get()
                if num_threads > 0:
                    cmd += f' -j {num_threads}'
                    self.log(f"启用多线程模式，使用 {num_threads} 个线程")
                else:
                    cmd += ' -j 0'  # 0表示使用所有可用线程
                    import os
                    available_cores = os.cpu_count()
                    self.log(f"启用多线程模式，自动使用所有可用线程 ({available_cores} 个核心)")
            else:
                self.log("使用单线程模式")
            
            # 统一工作目录为仓库根目录，确保输出在 <repo>/output 下
            helios_root = self._get_helios_root()
            self.log(f"执行命令: {cmd}")
            self.log(f"工作目录: {helios_root}")
            
            # 运行命令
            result = subprocess.run(
                cmd, 
                shell=True, 
                capture_output=True, 
                text=True, 
                cwd=helios_root
            )
            
            if result.returncode == 0:
                self.log(f"Helios运行成功，输出: {result.stdout[:200]}...")
                return True
            else:
                self.log(f"Helios运行失败，返回码: {result.returncode}")
                if result.stderr:
                    self.log(f"错误信息: {result.stderr}")
                if result.stdout:
                    self.log(f"输出信息: {result.stdout}")
                return False
                
        except Exception as e:
            self.log(f"运行Helios失败: {str(e)}")
            return False

    def batch_merge_las_files(self):
        """批量合并LAS文件"""
        if not self.output_folder.get() and not self.las_output_folder.get():
            messagebox.showerror("错误", "请先选择输出文件夹或LAS输出文件夹")
            return
        
        self.log("开始批量合并LAS文件...")
        
        # 确定搜索目录，优先使用LAS输出目录
        search_dirs = []
        if self.las_output_folder.get():
            search_dirs.append(self.las_output_folder.get())
            self.log(f"搜索LAS输出目录: {self.las_output_folder.get()}")
        
        if self.output_folder.get():
            search_dirs.append(self.output_folder.get())
            self.log(f"搜索输出目录: {self.output_folder.get()}")
        
        # 找到所有包含LAS文件的子文件夹
        las_folders = []
        for search_dir in search_dirs:
            for root, dirs, files in os.walk(search_dir):
                las_files_in_folder = [f for f in files if f.endswith(('.las', '.laz'))]
                if las_files_in_folder:
                    las_folders.append((root, las_files_in_folder))
        
        if not las_folders:
            messagebox.showerror("错误", "在指定文件夹中未找到LAS文件")
            return
        
        self.log(f"找到 {len(las_folders)} 个包含LAS文件的文件夹")
        
        success_count = 0
        failed_count = 0
        
        ts_pattern = re.compile(r'^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}$')
        for folder_path, las_files in las_folders:
            try:
                # 目标名称：若当前文件夹为时间戳，采用其父级名（survey名）；否则用当前文件夹名去掉后缀
                folder_name = os.path.basename(folder_path)
                parent_name = os.path.basename(os.path.dirname(folder_path))
                if ts_pattern.match(folder_name):
                    obj_name = parent_name
                else:
                    obj_name = folder_name
                    if obj_name.endswith('_las_output'):
                        obj_name = obj_name[:-11]
                    elif obj_name.endswith('_output'):
                        obj_name = obj_name[:-7]
                self.log(f"合并文件夹: {folder_name} -> 输出文件名: {obj_name} ({len(las_files)} 个LAS文件)")
                
                # 合并该文件夹中的所有LAS文件，传递正确的OBJ文件名
                success = self._merge_folder_las_files(folder_path, las_files, obj_name)
                
                if success:
                    success_count += 1
                    self.log(f"  ✓ {obj_name} 合并完成")
                else:
                    failed_count += 1
                    self.log(f"  ✗ {obj_name} 合并失败")
                
            except Exception as e:
                failed_count += 1
                obj_name = os.path.basename(folder_path).replace('_las_output', '').replace('_output', '')
                self.log(f"  ✗ {obj_name} 合并失败: {str(e)}")
        
        self.log(f"批量合并完成: 成功 {success_count} 个，失败 {failed_count} 个")
        messagebox.showinfo("完成", f"批量合并完成\n成功: {success_count} 个\n失败: {failed_count} 个")

    def _merge_folder_las_files(self, folder_path, las_files, custom_name=None):
        """合并单个文件夹中的LAS文件（内部方法）"""
        try:
            # 构建完整的文件路径列表
            full_las_files = [os.path.join(folder_path, f) for f in las_files]
            
            # 设置输出文件名 - 确保使用OBJ文件的原始名称
            if custom_name:
                output_filename = custom_name
                self.log(f"使用指定的文件名: {output_filename}")
            else:
                folder_name = os.path.basename(folder_path)
                parent_name = os.path.basename(os.path.dirname(folder_path))
                if re.match(r'^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}$', folder_name):
                    output_filename = parent_name
                else:
                    output_filename = folder_name
                    if output_filename.endswith('_las_output'):
                        output_filename = output_filename[:-11]
                    elif output_filename.endswith('_output'):
                        output_filename = output_filename[:-7]
                self.log(f"推断输出文件名: {folder_name} -> {output_filename}")
                    
            # 确定合并文件的保存位置
            if self.merge_output_folder.get():
                # 用户指定了合并输出文件夹，直接输出到该文件夹
                merge_root = self.merge_output_folder.get()
                merged_file = os.path.join(merge_root, f"{output_filename}.las")
                self.log(f"合并文件将保存到用户指定文件夹: {merged_file}")
            else:
                # 无用户指定时，若是时间戳文件夹，则保存到其父级（survey目录）；否则保存到当前文件夹
                folder_name = os.path.basename(folder_path)
                if re.match(r'^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}$', folder_name):
                    parent_dir = os.path.dirname(folder_path)
                    merged_file = os.path.join(parent_dir, f"{output_filename}.las")
                else:
                    merged_file = os.path.join(folder_path, f"{output_filename}.las")
            
            # 调用现有的合并方法逻辑
            return self._perform_las_merge(full_las_files, merged_file)
            
        except Exception as e:
            self.log(f"合并文件夹LAS文件失败: {str(e)}")
            return False

    def _perform_las_merge(self, las_files, output_file):
        """执行LAS文件合并的核心逻辑"""
        try:
            import laspy
            
            self.log(f"开始合并 {len(las_files)} 个LAS文件...")
            
            # 读取第一个文件获取header信息
            first_las = laspy.read(las_files[0])
            
            # 收集所有点数据
            all_x = [first_las.x]
            all_y = [first_las.y]
            all_z = [first_las.z]
            all_intensity = [first_las.intensity] if hasattr(first_las, 'intensity') else []
            all_return_number = [first_las.return_number] if hasattr(first_las, 'return_number') else []
            
            # 读取其他文件
            for las_file in las_files[1:]:
                las = laspy.read(las_file)
                all_x.append(las.x)
                all_y.append(las.y)
                all_z.append(las.z)
                if hasattr(las, 'intensity') and all_intensity:
                    all_intensity.append(las.intensity)
                if hasattr(las, 'return_number') and all_return_number:
                    all_return_number.append(las.return_number)
            
            # 合并数据
            import numpy as np
            merged_x = np.concatenate(all_x)
            merged_y = np.concatenate(all_y)
            merged_z = np.concatenate(all_z)
            
            # 创建新的LAS文件
            header = laspy.LasHeader(point_format=first_las.header.point_format, version=first_las.header.version)
            header.x_scale = first_las.header.x_scale
            header.y_scale = first_las.header.y_scale
            header.z_scale = first_las.header.z_scale
            header.x_offset = first_las.header.x_offset
            header.y_offset = first_las.header.y_offset
            header.z_offset = first_las.header.z_offset
            
            merged_las = laspy.LasData(header)
            merged_las.x = merged_x
            merged_las.y = merged_y
            merged_las.z = merged_z
            
            if all_intensity:
                merged_las.intensity = np.concatenate(all_intensity)
            if all_return_number:
                merged_las.return_number = np.concatenate(all_return_number)
            
            # 写入文件
            merged_las.write(output_file)
            
            self.log(f"合并完成，共 {len(merged_x)} 个点，保存到: {output_file}")
            return True
            
        except ImportError:
            self.log("错误: 需要安装laspy库来合并LAS文件")
            self.log("请运行: pip install laspy")
            return False
        except Exception as e:
            self.log(f"合并LAS文件失败: {str(e)}")
            return False

    def generate_scene_file(self, obj_path):
        """生成场景文件"""
        try:
            # 获取参数
            add_ground = self.add_ground.get()
            
            # 确保输出目录存在
            if hasattr(self, 'output_directory') and self.output_directory:
                output_folder = self.output_directory
            else:
                output_folder = self.output_folder.get()
            
            os.makedirs(output_folder, exist_ok=True)
            
            # 生成场景文件路径
            base_name = os.path.splitext(os.path.basename(obj_path))[0]
            if base_name.endswith('_triangulated'):
                base_name = base_name.replace('_triangulated', '')
            scene_xml_path = os.path.join(output_folder, f"{base_name}_scene.xml")
            
            # 生成场景文件
            self.generate_scene_xml(obj_path, scene_xml_path, add_ground=add_ground)
            
            self.log(f"场景文件生成完成: {scene_xml_path}")
            self.scene_file_path = scene_xml_path
            return True
            
        except Exception as e:
            self.log(f"生成场景文件失败: {str(e)}")
            return False

    def generate_survey_file(self):
        """生成调查文件"""
        try:
            # 获取参数
            step = self.step.get()
            z_height = self.z_height.get()
            max_points = self.max_points.get()
            boundary_distance = self.boundary_distance.get()
            
            # 获取当前处理的OBJ文件路径
            obj_path = self.obj_path.get()
            
            # 解析OBJ文件
            min_xyz, max_xyz, vertices, faces = self.parse_obj_bbox(obj_path)
            
            # 提取房屋轮廓
            boundary_points = self.extract_floor_plan(vertices, faces)
            
            # 优化扫描路径
            scan_path = self.optimize_scan_path(boundary_points, step=step, z_height=z_height, max_points=max_points, boundary_distance=boundary_distance)
            
            # 生成文件路径
            if hasattr(self, 'output_directory') and self.output_directory:
                output_folder = self.output_directory
            else:
                output_folder = self.output_folder.get()
            
            base_name = os.path.splitext(os.path.basename(obj_path))[0]
            if base_name.endswith('_triangulated'):
                base_name = base_name.replace('_triangulated', '')
            
            survey_xml_path = os.path.join(output_folder, f"{base_name}_survey.xml")
            visualization_path = os.path.join(output_folder, f"{base_name}_path.png")
            
            # 生成survey文件
            if hasattr(self, 'scene_file_path') and self.scene_file_path:
                scene_xml_path = self.scene_file_path
            else:
                scene_xml_path = os.path.join(output_folder, f"{base_name}_scene.xml")
            
            las_output_root = self.las_output_folder.get() if self.las_output_folder.get() else None
            self.generate_optimized_survey_xml(scene_xml_path, scan_path, survey_xml_path, z_height=z_height, las_output_root=las_output_root)
            
            # 可视化扫描路径
            self.visualize_scan_path(boundary_points, scan_path, visualization_path, boundary_distance)
            
            self.log(f"调查文件生成完成: {survey_xml_path}")
            self.log(f"扫描点数量: {len(scan_path)} 个")
            self.log(f"边界距离: {boundary_distance:.2f} 米")
            
            self.survey_file_path = survey_xml_path
            return True
            
        except Exception as e:
            self.log(f"生成调查文件失败: {str(e)}")
            return False

    def triangulate_obj_file(self, obj_path):
        """三角化OBJ文件"""
        try:
            self.log("开始三角化OBJ文件...")
            
            # 创建三角化器
            triangulator = AdvancedOBJTriangulator()
            
            # 获取文件名（不含扩展名）
            base_name = os.path.splitext(os.path.basename(obj_path))[0]
            
            # 在当前输出目录中生成三角化文件路径
            if hasattr(self, 'output_directory') and self.output_directory:
                output_dir = self.output_directory
            else:
                output_dir = self.output_folder.get()
            
            # 确保输出目录存在
            os.makedirs(output_dir, exist_ok=True)
            
            # 生成三角化文件的完整路径
            triangulated_path = os.path.join(output_dir, f"{base_name}_triangulated.obj")
            
            # 处理文件
            success, output_file = triangulator.process_file(obj_path, triangulated_path)
            
            if success:
                self.log(f"OBJ文件三角化完成: {output_file}")
                return output_file
            else:
                self.log("OBJ文件三角化失败")
                return obj_path  # 返回原文件路径
                
        except Exception as e:
            self.log(f"三角化过程中出错: {e}")
            return obj_path  # 返回原文件路径
    
    def parse_obj_bbox(self, obj_path):
        """解析OBJ文件，获取顶点和边界框"""
        vertices = []
        faces = []
        
        # 尝试多种编码方式读取文件
        encodings = ['utf-8', 'gbk', 'gb2312', 'latin-1', 'cp1252']
        file_content = None
        
        for encoding in encodings:
            try:
                with open(obj_path, 'r', encoding=encoding) as f:
                    file_content = f.readlines()
                self.log(f"成功使用 {encoding} 编码读取OBJ文件")
                break
            except UnicodeDecodeError:
                continue
        
        if file_content is None:
            # 如果所有编码都失败，使用二进制模式读取并忽略错误
            try:
                with open(obj_path, 'r', encoding='utf-8', errors='ignore') as f:
                    file_content = f.readlines()
                self.log("使用UTF-8编码（忽略错误）读取OBJ文件")
            except Exception as e:
                raise Exception(f"无法读取OBJ文件 {obj_path}: {e}")
        
        # 解析文件内容
        for line in file_content:
            line = line.strip()
            if line.startswith('v '):
                parts = line.split()
                if len(parts) >= 4:
                    try:
                        x, y, z = map(float, parts[1:4])
                        vertices.append([x, y, z])
                    except ValueError:
                        continue
            elif line.startswith('f '):
                parts = line.split()
                face_vertices = []
                for part in parts[1:]:
                    try:
                        vertex_idx = int(part.split('/')[0]) - 1
                        face_vertices.append(vertex_idx)
                    except (ValueError, IndexError):
                        continue
                if face_vertices:
                    faces.append(face_vertices)
        
        vertices = np.array(vertices)
        min_xyz = vertices.min(axis=0)
        max_xyz = vertices.max(axis=0)
        return min_xyz, max_xyz, vertices, faces
    
    def extract_floor_plan(self, vertices, faces, height_threshold=0.1):
        """提取房屋的平面轮廓"""
        z_values = vertices[:, 2]
        ground_height = np.percentile(z_values, 5)
        
        ground_vertices = []
        for face in faces:
            face_vertices = [vertices[idx] for idx in face]
            face_z_avg = np.mean([v[2] for v in face_vertices])
            if abs(face_z_avg - ground_height) < height_threshold:
                ground_vertices.extend(face_vertices)
        
        if not ground_vertices:
            ground_vertices = vertices
        
        xy_coords = [(v[0], v[1]) for v in ground_vertices]
        
        if HAS_SCIPY and len(xy_coords) >= 3:
            try:
                hull = ConvexHull(xy_coords)
                boundary_points = [xy_coords[i] for i in hull.vertices]
                boundary_points.append(boundary_points[0])
                return boundary_points
            except:
                pass
        
        # 如果scipy不可用或ConvexHull失败，使用简单的边界框
        min_x, min_y = min(xy_coords, key=lambda p: p[0])[0], min(xy_coords, key=lambda p: p[1])[1]
        max_x, max_y = max(xy_coords, key=lambda p: p[0])[0], max(xy_coords, key=lambda p: p[1])[1]
        return [(min_x, min_y), (max_x, min_y), (max_x, max_y), (min_x, max_y), (min_x, min_y)]
    
    def generate_scene_xml(self, obj_path, scene_xml_path, add_ground=False):
        """生成场景XML文件，可选择添加地面"""
        ground_part = ""
        if add_ground:
            ground_part = '''
        <part id="1">
            <filter type="groundplane">
                <param type="double" key="xSize" value="50" />
                <param type="double" key="ySize" value="50" />
                <param type="double" key="z" value="0" />
            </filter>
        </part>'''
        
        scene_xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<document>
    <scene id="auto_scene" name="Auto Generated Scene">
        <part id="0">
            <filter type="objloader">
                <param type="string" key="filepath" value="{obj_path}"/>
                <param type="string" key="up" value="z" />
            </filter>
            <filter type="translate">
                <param type="vec3" key="offset" value="0;0;0" />
            </filter>
            <filter type="scale">
                <param type="double" key="scale" value="1.0" />
            </filter>
        </part>{ground_part}
    </scene>
</document>
'''
        with open(scene_xml_path, 'w', encoding='utf-8') as f:
            f.write(scene_xml)
        self.log(f"已生成 scene.xml: {scene_xml_path}")
        if add_ground:
            self.log("已添加地面平面")
    
    def optimize_scan_path(self, boundary_points, step=1.0, z_height=1.5, max_points=15, boundary_distance=0.5):
        """根据选择的模式生成扫描路径"""
        if self.grid_scan_mode.get():
            return self._generate_grid_scan_path(boundary_points, step, z_height, boundary_distance)
        else:
            return self._generate_traditional_scan_path(boundary_points, step, z_height, max_points, boundary_distance)
    
    def _generate_grid_scan_path(self, boundary_points, step=1.0, z_height=1.5, boundary_distance=0.5):
        """生成网状扫描路径，根据选择的方向进行扫描"""
        boundary_coords = boundary_points[:-1]
        house_polygon = Polygon(boundary_coords)
        
        # 创建缩小的多边形，远离边界指定距离
        if boundary_distance > 0:
            try:
                inner_polygon = house_polygon.buffer(-boundary_distance)
                
                if not inner_polygon.is_valid or inner_polygon.is_empty:
                    self.log(f"警告: 边界距离 {boundary_distance:.2f}m 过大，无法创建有效的内部区域")
                    self.log("使用房屋中心点作为扫描位置")
                    centroid = house_polygon.centroid
                    return [(centroid.x, centroid.y)]
                
                if hasattr(inner_polygon, 'geoms'):
                    areas = [geom.area for geom in inner_polygon.geoms]
                    max_area_idx = areas.index(max(areas))
                    inner_polygon = inner_polygon.geoms[max_area_idx]
                
                scan_polygon = inner_polygon
                self.log(f"应用边界距离: {boundary_distance:.2f}m，缩小扫描区域")
                
            except Exception as e:
                self.log(f"创建内部扫描区域时出错: {e}")
                self.log("使用原始边界区域")
                scan_polygon = house_polygon
        else:
            scan_polygon = house_polygon
        
        min_x, min_y, max_x, max_y = scan_polygon.bounds
        
        # 根据选择的扫描方向生成路径
        scan_direction = self.scan_direction.get()
        scan_path = []
        
        if scan_direction == "horizontal":
            # 纯水平扫描（左右扫描）
            scan_path = self._generate_horizontal_scan(scan_polygon, min_x, max_x, min_y, max_y, step)
            scan_type = "水平扫描"
            
        elif scan_direction == "vertical":
            # 纯垂直扫描（上下扫描）
            scan_path = self._generate_vertical_scan(scan_polygon, min_x, max_x, min_y, max_y, step)
            scan_type = "垂直扫描"
            
        elif scan_direction == "both":
            # 双向扫描：先水平后垂直，分为两个阶段
            horizontal_path = self._generate_horizontal_scan(scan_polygon, min_x, max_x, min_y, max_y, step)
            vertical_path = self._generate_vertical_scan(scan_polygon, min_x, max_x, min_y, max_y, step)
            scan_path = horizontal_path + vertical_path
            scan_type = "双向扫描（先水平后垂直）"
            
        elif scan_direction == "grid":
            # 网格点扫描：生成规则网格点
            scan_path = self._generate_grid_points(scan_polygon, min_x, max_x, min_y, max_y, step)
            scan_type = "网格点扫描"
        
        if not scan_path:
            self.log("警告: 未找到有效的扫描点，使用中心点")
            centroid = scan_polygon.centroid
            scan_path = [(centroid.x, centroid.y)]
        
        # 记录扫描配置信息
        self.log(f"网格扫描配置:")
        self.log(f"  - 扫描类型: {scan_type}")
        self.log(f"  - 网格步长: {step:.2f} 米")
        self.log(f"  - 边界距离: {boundary_distance:.2f} 米")
        self.log(f"  - 总扫描点数: {len(scan_path)} 个")
        self.log(f"  - 扫描区域: ({min_x:.1f}, {min_y:.1f}) 到 ({max_x:.1f}, {max_y:.1f})")
        
        return scan_path
    
    def _generate_horizontal_scan(self, scan_polygon, min_x, max_x, min_y, max_y, step):
        """生成水平方向扫描路径"""
        scan_path = []
        y_positions = np.arange(min_y + step/2, max_y, step)
        
        for i, y in enumerate(y_positions):
            # 找到这一行的有效X范围
            x_points = []
            x_test_points = np.arange(min_x, max_x + step/20, step/20)
            for x in x_test_points:
                if scan_polygon.contains(Point(x, y)):
                    x_points.append(x)
            
            if x_points:
                x_start = min(x_points)
                x_end = max(x_points)
                x_scan_points = np.arange(x_start, x_end + step/2, step)
                
                # 蛇形扫描：奇数行从左到右，偶数行从右到左
                if i % 2 == 1:
                    x_scan_points = x_scan_points[::-1]
                
                for x in x_scan_points:
                    if scan_polygon.contains(Point(x, y)):
                        scan_path.append((x, y))
        
        self.log(f"    生成 {len(y_positions)} 条水平扫描线，共 {len(scan_path)} 个点")
        return scan_path
    
    def _generate_vertical_scan(self, scan_polygon, min_x, max_x, min_y, max_y, step):
        """生成垂直方向扫描路径"""
        scan_path = []
        x_positions = np.arange(min_x + step/2, max_x, step)
        
        for i, x in enumerate(x_positions):
            # 找到这一列的有效Y范围
            y_points = []
            y_test_points = np.arange(min_y, max_y + step/20, step/20)
            for y in y_test_points:
                if scan_polygon.contains(Point(x, y)):
                    y_points.append(y)
            
            if y_points:
                y_start = min(y_points)
                y_end = max(y_points)
                y_scan_points = np.arange(y_start, y_end + step/2, step)
                
                # 蛇形扫描：奇数列从下到上，偶数列从上到下
                if i % 2 == 1:
                    y_scan_points = y_scan_points[::-1]
                
                for y in y_scan_points:
                    if scan_polygon.contains(Point(x, y)):
                        scan_path.append((x, y))
        
        self.log(f"    生成 {len(x_positions)} 条垂直扫描线，共 {len(scan_path)} 个点")
        return scan_path
    
    def _generate_grid_points(self, scan_polygon, min_x, max_x, min_y, max_y, step):
        """生成网格点扫描路径，使用最短路径连接"""
        scan_path = []
        
        # 生成所有网格点
        grid_points = []
        x_positions = np.arange(min_x + step/2, max_x, step)
        y_positions = np.arange(min_y + step/2, max_y, step)
        
        for x in x_positions:
            for y in y_positions:
                if scan_polygon.contains(Point(x, y)):
                    grid_points.append((x, y))
        
        if not grid_points:
            return []
        
        # 使用最近邻算法连接网格点，形成最短路径
        unvisited = grid_points.copy()
        if unvisited:
            current = unvisited.pop(0)  # 从第一个点开始
            scan_path = [current]
            
            while unvisited:
                # 找到距离当前点最近的未访问点
                distances = [np.sqrt((current[0] - p[0])**2 + (current[1] - p[1])**2) for p in unvisited]
                nearest_idx = distances.index(min(distances))
                current = unvisited.pop(nearest_idx)
                scan_path.append(current)
        
        self.log(f"    生成 {len(x_positions)} x {len(y_positions)} 网格，有效点 {len(scan_path)} 个")
        return scan_path
    
    def _generate_traditional_scan_path(self, boundary_points, step=1.0, z_height=1.5, max_points=15, boundary_distance=0.5):
        """传统扫描路径，限制最大点数并使用最近邻优化"""
        boundary_coords = boundary_points[:-1]
        house_polygon = Polygon(boundary_coords)
        
        # 创建缩小的多边形，远离边界指定距离
        if boundary_distance > 0:
            try:
                inner_polygon = house_polygon.buffer(-boundary_distance)
                
                if not inner_polygon.is_valid or inner_polygon.is_empty:
                    self.log(f"警告: 边界距离 {boundary_distance:.2f}m 过大，无法创建有效的内部区域")
                    centroid = house_polygon.centroid
                    return [(centroid.x, centroid.y)]
                
                if hasattr(inner_polygon, 'geoms'):
                    areas = [geom.area for geom in inner_polygon.geoms]
                    max_area_idx = areas.index(max(areas))
                    inner_polygon = inner_polygon.geoms[max_area_idx]
                
                scan_polygon = inner_polygon
                self.log(f"应用边界距离: {boundary_distance:.2f}m，缩小扫描区域")
                
            except Exception as e:
                self.log(f"创建内部扫描区域时出错: {e}")
                scan_polygon = house_polygon
        else:
            scan_polygon = house_polygon
        
        min_x, min_y, max_x, max_y = scan_polygon.bounds
        
        # 动态调整步长以达到目标点数
        target_points = max_points
        current_step = step
        
        for attempt in range(10):  # 最多尝试10次
            x_range = np.arange(min_x + current_step/2, max_x - current_step/2, current_step)
            y_range = np.arange(min_y + current_step/2, max_y - current_step/2, current_step)
            
            valid_points = []
            for x in x_range:
                for y in y_range:
                    point = Point(x, y)
                    if scan_polygon.contains(point):
                        valid_points.append((x, y))
            
            if len(valid_points) <= target_points:
                break
            
            # 增加步长以减少点数
            current_step *= 1.2
        
        if not valid_points:
            centroid = scan_polygon.centroid
            valid_points = [(centroid.x, centroid.y)]
        
        # 如果点数仍然过多，随机选择目标数量的点
        if len(valid_points) > target_points:
            valid_points = random.sample(valid_points, target_points)
        
        # 使用最近邻算法优化路径
        def nearest_neighbor_path(points):
            if len(points) <= 1:
                return points
            
            unvisited = points.copy()
            path = [unvisited.pop(0)]
            
            while unvisited:
                current = path[-1]
                nearest_idx = min(range(len(unvisited)), 
                                key=lambda i: np.linalg.norm(np.array(current) - np.array(unvisited[i])))
                path.append(unvisited.pop(nearest_idx))
            
            return path
        
        optimized_path = nearest_neighbor_path(valid_points)
        
        self.log(f"传统扫描配置:")
        self.log(f"  - 初始步长: {step:.2f} 米")
        self.log(f"  - 调整后步长: {current_step:.2f} 米")
        self.log(f"  - 边界距离: {boundary_distance:.2f} 米")
        self.log(f"  - 目标最大点数: {target_points}")
        self.log(f"  - 实际扫描点数: {len(optimized_path)}")
        
        return optimized_path
    
    def _generate_serpentine_path(self, grid_points, x_range, y_range, step):
        """生成蛇形扫描路径，减少移动距离"""
        if not grid_points:
            return grid_points
        
        # 将点按坐标组织成网格
        point_grid = {}
        for x, y in grid_points:
            # 找到最接近的网格索引
            x_idx = int(round((x - x_range[0]) / step))
            y_idx = int(round((y - y_range[0]) / step))
            point_grid[(x_idx, y_idx)] = (x, y)
        
        # 生成蛇形路径
        serpentine_path = []
        x_indices = sorted(set(x_idx for x_idx, y_idx in point_grid.keys()))
        
        for i, x_idx in enumerate(x_indices):
            # 获取当前X列的所有Y坐标
            y_indices = sorted([y_idx for (xi, y_idx) in point_grid.keys() if xi == x_idx])
            
            # 奇数列从下到上，偶数列从上到下（蛇形）
            if i % 2 == 0:
                y_indices = sorted(y_indices)  # 从下到上
            else:
                y_indices = sorted(y_indices, reverse=True)  # 从上到下
            
            # 添加该列的所有点
            for y_idx in y_indices:
                if (x_idx, y_idx) in point_grid:
                    serpentine_path.append(point_grid[(x_idx, y_idx)])
        
        return serpentine_path
    
    def generate_optimized_survey_xml(self, scene_xml_path, scan_path, survey_xml_path, z_height=1.5, las_output_root=None):
        """生成优化的survey文件"""
        legs = []
        for i, (x, y) in enumerate(scan_path):
            legs.append(f'''
        <leg>
            <platformSettings x="{x:.2f}" y="{y:.2f}" z="{z_height}" onGround="false" movePerSec_m="0.8"/>
            <scannerSettings template="handheld_360_optimized" trajectoryTimeInterval_s="0.1"/>
        </leg>''')

        # 获取Helios根目录的绝对路径（健壮定位）
        helios_root = self._get_helios_root()

        # 构建配置文件的绝对路径
        scanner_config_path = os.path.join(helios_root, "python", "pyhelios", "data", "scanners_als.xml")
        platform_config_path = os.path.join(helios_root, "python", "pyhelios", "data", "platforms.xml")

        # 如果文件不存在，尝试其他可能的路径
        if not os.path.exists(scanner_config_path):
            scanner_config_path = "../../python/pyhelios/data/scanners_als.xml"
        if not os.path.exists(platform_config_path):
            platform_config_path = "../../python/pyhelios/data/platforms.xml"

        # 名称基础：使用OBJ基础名（同步为 survey 的 name），不再创建 _las_output 目录
        base_name = os.path.splitext(os.path.basename(survey_xml_path))[0].replace('_survey', '')
        survey_name = base_name
        self.log(f"使用扫描器配置文件: {scanner_config_path}")
        self.log(f"使用平台配置文件: {platform_config_path}")

        survey_xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<document>
    <scannerSettings id="handheld_360_optimized" active="true" pulseFreq_hz="10000" scanAngle_deg="360" scanFreq_hz="100" />
    <survey name="{survey_name}"
            scene="{scene_xml_path}#auto_scene"
            platform="{platform_config_path}#indoor_ultra_precision"
            scanner="{scanner_config_path}#riegl_vux-1uav22">
        <FWFSettings beamSampleQuality="4" binSize_ns="0.1" winSize_ns="0.5"/>
        <detectorSettings rangeMax_m="8.0" rangeMin_m="0.05"/>
        {''.join(legs)}
    </survey>
</document>
'''
        with open(survey_xml_path, 'w', encoding='utf-8') as f:
            f.write(survey_xml)
        self.log(f"已生成优化的 survey.xml: {survey_xml_path}")
    
    def visualize_scan_path(self, boundary_points, scan_path, output_path, boundary_distance=0.0):
        """可视化网格扫描路径"""
        try:
            boundary_coords = np.array(boundary_points[:-1])
            plt.figure(figsize=(12, 10))
            
            # 绘制房屋轮廓
            plt.plot(boundary_coords[:, 0], boundary_coords[:, 1], 'b-', linewidth=2.5, label='房屋轮廓')
            
            # 如果有边界距离，显示内缩的边界
            if boundary_distance > 0:
                try:
                    house_polygon = Polygon(boundary_points[:-1])
                    inner_polygon = house_polygon.buffer(-boundary_distance)
                    
                    if not inner_polygon.is_empty and inner_polygon.is_valid:
                        # 如果是MultiPolygon，选择最大的
                        if hasattr(inner_polygon, 'geoms'):
                            areas = [geom.area for geom in inner_polygon.geoms]
                            max_area_idx = areas.index(max(areas))
                            inner_polygon = inner_polygon.geoms[max_area_idx]
                        
                        # 获取内缩边界的坐标
                        if hasattr(inner_polygon, 'exterior'):
                            inner_coords = np.array(inner_polygon.exterior.coords)
                            plt.plot(inner_coords[:, 0], inner_coords[:, 1], 'g--', linewidth=2, 
                                   label=f'扫描边界 (远离 {boundary_distance:.1f}m)')
                except Exception as e:
                    self.log(f"绘制内缩边界时出错: {e}")
            
            if scan_path:
                path_coords = np.array(scan_path)
                
                if self.grid_scan_mode.get():
                    # 网格扫描模式：根据扫描方向显示不同的可视化
                    scan_direction = self.scan_direction.get()
                    
                    # 绘制所有扫描点
                    plt.scatter(path_coords[:, 0], path_coords[:, 1], c='red', s=20, alpha=0.8, 
                               label=f'扫描点 ({len(scan_path)}个)', zorder=5)
                    
                    step = self.step.get()
                    
                    if scan_direction == "horizontal":
                        # 只显示水平扫描线
                        unique_y = sorted(set(np.round(path_coords[:, 1] / step) * step))
                        for y in unique_y:
                            x_points = sorted([x for x, y_coord in scan_path if abs(y_coord - y) < step/2])
                            if len(x_points) > 1:
                                plt.plot([min(x_points), max(x_points)], [y, y], 'r-', 
                                       linewidth=2, alpha=0.7, zorder=3)
                        plt.plot([], [], 'r-', linewidth=2, alpha=0.7, label='水平扫描线')
                        
                    elif scan_direction == "vertical":
                        # 只显示垂直扫描线
                        unique_x = sorted(set(np.round(path_coords[:, 0] / step) * step))
                        for x in unique_x:
                            y_points = sorted([y for x_coord, y in scan_path if abs(x_coord - x) < step/2])
                            if len(y_points) > 1:
                                plt.plot([x, x], [min(y_points), max(y_points)], 'r-', 
                                       linewidth=2, alpha=0.7, zorder=3)
                        plt.plot([], [], 'r-', linewidth=2, alpha=0.7, label='垂直扫描线')
                        
                    elif scan_direction == "both":
                        # 显示双向扫描线（用不同颜色区分）
                        unique_x = sorted(set(np.round(path_coords[:, 0] / step) * step))
                        unique_y = sorted(set(np.round(path_coords[:, 1] / step) * step))
                        
                        # 水平线（蓝色）
                        for y in unique_y:
                            x_points = sorted([x for x, y_coord in scan_path if abs(y_coord - y) < step/2])
                            if len(x_points) > 1:
                                plt.plot([min(x_points), max(x_points)], [y, y], 'b-', 
                                       linewidth=1.5, alpha=0.6, zorder=3)
                        
                        # 垂直线（绿色）
                        for x in unique_x:
                            y_points = sorted([y for x_coord, y in scan_path if abs(x_coord - x) < step/2])
                            if len(y_points) > 1:
                                plt.plot([x, x], [min(y_points), max(y_points)], 'g-', 
                                       linewidth=1.5, alpha=0.6, zorder=3)
                        
                        plt.plot([], [], 'b-', linewidth=1.5, alpha=0.6, label='水平扫描线')
                        plt.plot([], [], 'g-', linewidth=1.5, alpha=0.6, label='垂直扫描线')
                        
                    elif scan_direction == "grid":
                        # 网格点扫描：显示连接路径
                        plt.plot(path_coords[:, 0], path_coords[:, 1], 'orange', linewidth=1.5, alpha=0.8, 
                                label='网格连接路径', zorder=4)
                        
                        # 添加方向箭头
                        step_size = max(1, len(scan_path) // 15)
                        for i in range(0, len(scan_path) - 1, step_size):
                            dx = path_coords[i+1, 0] - path_coords[i, 0]
                            dy = path_coords[i+1, 1] - path_coords[i, 1]
                            if abs(dx) > 1e-6 or abs(dy) > 1e-6:
                                plt.arrow(path_coords[i, 0], path_coords[i, 1], dx*0.3, dy*0.3,
                                        head_width=0.03, head_length=0.03, fc='darkorange', ec='darkorange',
                                        alpha=0.8, zorder=3)
                    
                    # 标出起始点和结束点
                    plt.plot(path_coords[0, 0], path_coords[0, 1], 'go', markersize=8, 
                            label='起始点', zorder=6)
                    if len(scan_path) > 1:
                        plt.plot(path_coords[-1, 0], path_coords[-1, 1], 'mo', markersize=8, 
                                label='结束点', zorder=6)
                
                else:
                    # 传统扫描模式：显示路径和箭头
                    
                    # 绘制扫描点
                    plt.scatter(path_coords[:, 0], path_coords[:, 1], c='red', s=30, alpha=0.7, 
                               label=f'扫描点 ({len(scan_path)}个)', zorder=5)
                    
                    # 绘制扫描路径
                    plt.plot(path_coords[:, 0], path_coords[:, 1], 'r-', linewidth=1.5, alpha=0.8, 
                            label='扫描路径', zorder=4)
                    
                    # 标出起始点和结束点
                    plt.plot(path_coords[0, 0], path_coords[0, 1], 'go', markersize=10, 
                            label='起始点', zorder=6)
                    if len(scan_path) > 1:
                        plt.plot(path_coords[-1, 0], path_coords[-1, 1], 'mo', markersize=10, 
                                label='结束点', zorder=6)
                    
                    # 添加方向箭头（每隔几个点显示一次，避免太密集）
                    step_size = max(1, len(scan_path) // 10)  # 最多显示10个箭头
                    for i in range(0, len(scan_path) - 1, step_size):
                        dx = path_coords[i+1, 0] - path_coords[i, 0]
                        dy = path_coords[i+1, 1] - path_coords[i, 1]
                        if abs(dx) > 1e-6 or abs(dy) > 1e-6:  # 避免零长度箭头
                            plt.arrow(path_coords[i, 0], path_coords[i, 1], dx*0.3, dy*0.3,
                                    head_width=0.05, head_length=0.05, fc='orange', ec='orange',
                                    alpha=0.8, zorder=3)
            
            plt.xlabel('X 坐标 (米)', fontsize=12)
            plt.ylabel('Y 坐标 (米)', fontsize=12)
            
            # 根据当前模式设置标题
            if self.grid_scan_mode.get():
                scan_direction = self.scan_direction.get()
                direction_names = {
                    "horizontal": "水平扫描",
                    "vertical": "垂直扫描", 
                    "both": "双向扫描",
                    "grid": "网格点扫描"
                }
                title = f'{direction_names.get(scan_direction, "网格扫描")}路径规划'
            else:
                title = '传统扫描路径规划'
            
            if boundary_distance > 0:
                title += f' (边界距离: {boundary_distance:.1f}m)'
            plt.title(title, fontsize=14, fontweight='bold')
            plt.legend(loc='best', fontsize=10)
            plt.grid(True, alpha=0.3)
            plt.axis('equal')
            
            # 添加统计信息文本框
            if scan_path:
                if self.grid_scan_mode.get():
                    # 网格扫描模式的统计信息
                    step = self.step.get()
                    scan_direction = self.scan_direction.get()
                    
                    stats_text = f'{direction_names.get(scan_direction, "网格扫描")}统计:\n'
                    stats_text += f'总扫描点: {len(scan_path)}个\n'
                    stats_text += f'网格间距: {step:.2f}m\n'
                    
                    if scan_direction in ["horizontal", "both"]:
                        unique_y = len(set(np.round(path_coords[:, 1] / step) * step))
                        stats_text += f'水平线: {unique_y}条\n'
                    
                    if scan_direction in ["vertical", "both"]:
                        unique_x = len(set(np.round(path_coords[:, 0] / step) * step))
                        stats_text += f'垂直线: {unique_x}条\n'
                    
                    if scan_direction == "grid":
                        # 计算网格点路径总长度
                        total_distance = 0
                        for i in range(len(scan_path) - 1):
                            dx = scan_path[i+1][0] - scan_path[i][0]
                            dy = scan_path[i+1][1] - scan_path[i][1]
                            total_distance += np.sqrt(dx*dx + dy*dy)
                        stats_text += f'连接路径: {total_distance:.1f}m\n'
                        
                else:
                    # 传统扫描模式的统计信息
                    total_distance = 0
                    for i in range(len(scan_path) - 1):
                        dx = scan_path[i+1][0] - scan_path[i][0]
                        dy = scan_path[i+1][1] - scan_path[i][1]
                        total_distance += np.sqrt(dx*dx + dy*dy)
                    
                    stats_text = f'扫描点数: {len(scan_path)}\n路径长度: {total_distance:.1f}m'
                
                if boundary_distance > 0:
                    stats_text += f'边界距离: {boundary_distance:.1f}m'
                
                plt.text(0.02, 0.98, stats_text, transform=plt.gca().transAxes, 
                        verticalalignment='top', bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
            
            plt.tight_layout()
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            plt.close()
            self.log(f"网格扫描路径可视化已保存到: {output_path}")
        except Exception as e:
            self.log(f"可视化失败: {e}")
    
    def generate_scene_and_survey(self):
        """生成场景和调查文件"""
        def run_generation():
            try:
                obj_path = self.obj_path.get()
                output_folder = self.output_folder.get()
                
                if not obj_path or not os.path.exists(obj_path):
                    messagebox.showerror("错误", "请选择有效的OBJ文件")
                    return
                
                if not output_folder:
                    messagebox.showerror("错误", "请选择输出文件夹")
                    return
                
                # 创建输出文件夹
                os.makedirs(output_folder, exist_ok=True)
                self.output_directory = output_folder  # 保存输出目录供LAS合并使用
                
                # 获取参数
                step = self.step.get()
                z_height = self.z_height.get()
                add_ground = self.add_ground.get()
                max_points = self.max_points.get()
                auto_triangulate = self.auto_triangulate.get()
                boundary_distance = self.boundary_distance.get()
                
                self.log("开始生成场景和调查文件...")
                
                # 如果启用自动三角化，先处理OBJ文件
                processed_obj_path = obj_path
                if auto_triangulate:
                    processed_obj_path = self.triangulate_obj_file(obj_path)
                else:
                    self.log("跳过三角化步骤")
                
                # 解析OBJ文件
                min_xyz, max_xyz, vertices, faces = self.parse_obj_bbox(processed_obj_path)
                self.log(f"OBJ包围盒 min: {min_xyz}, max: {max_xyz}")
                self.log(f"房屋高度: {max_xyz[2] - min_xyz[2]:.2f} 米")
                
                # 提取房屋轮廓
                boundary_points = self.extract_floor_plan(vertices, faces)
                self.log(f"房屋轮廓包含 {len(boundary_points)-1} 个边界点")
                
                # 生成文件路径
                base_name = os.path.splitext(os.path.basename(obj_path))[0]
                scene_xml_path = os.path.join(output_folder, f"{base_name}_scene.xml")
                survey_xml_path = os.path.join(output_folder, f"{base_name}_survey.xml")
                visualization_path = os.path.join(output_folder, f"{base_name}_path.png")
                
                # 生成场景文件（使用处理后的OBJ文件）
                self.generate_scene_xml(processed_obj_path, scene_xml_path, add_ground=add_ground)
                
                # 优化扫描路径
                scan_path = self.optimize_scan_path(boundary_points, step=step, z_height=z_height, max_points=max_points, boundary_distance=boundary_distance)
                
                # 生成优化的survey文件
                las_output_root = self.las_output_folder.get() if self.las_output_folder.get() else None
                self.generate_optimized_survey_xml(scene_xml_path, scan_path, survey_xml_path, z_height=z_height, las_output_root=las_output_root)
                
                # 可视化扫描路径
                self.visualize_scan_path(boundary_points, scan_path, visualization_path, boundary_distance)
                
                self.log("\n=== 生成完成 ===")
                self.log(f"1. 扫描点数量: {len(scan_path)} 个")
                self.log(f"2. 扫描路径总长度: {len(scan_path) * step:.1f} 米")
                self.log(f"3. 路径确保不超出房屋轮廓")
                self.log(f"4. 使用最近邻算法优化路径长度")
                self.log(f"5. 边界距离: {boundary_distance:.2f} 米")
                self.log(f"6. 地面选项: {'已添加' if add_ground else '未添加'}")
                self.log(f"7. 三角化选项: {'已启用' if auto_triangulate else '未启用'}")
                self.log(f"8. 输出文件夹: {output_folder}")
                self.log(f"9. Survey文件: {survey_xml_path}")
                
                # 保存survey文件路径供后续使用
                self.survey_file_path = survey_xml_path
                
                messagebox.showinfo("完成", "场景和调查文件生成完成！")
                
            except Exception as e:
                self.log(f"生成过程中出现错误: {e}")
                messagebox.showerror("错误", f"生成过程中出现错误: {e}")
        
        # 在新线程中运行生成过程
        thread = threading.Thread(target=run_generation)
        thread.daemon = True
        thread.start()
    
    def run_helios(self):
        """运行Helios"""
        if not hasattr(self, 'survey_file_path') or not self.survey_file_path or not os.path.exists(self.survey_file_path):
            messagebox.showerror("错误", "请先生成survey文件")
            return
        
        def run_helios_command():
            try:
                self.log("开始运行Helios...")
                
                # 构建基础命令
                cmd = f'helios "{self.survey_file_path}" --lasOutput'
                
                # 添加多线程支持
                if self.enable_multithreading.get():
                    num_threads = self.num_threads.get()
                    if num_threads > 0:
                        cmd += f' -j {num_threads}'
                        self.log(f"启用多线程模式，使用 {num_threads} 个线程")
                    else:
                        cmd += ' -j 0'  # 0表示使用所有可用线程
                        import os
                        available_cores = os.cpu_count()
                        self.log(f"启用多线程模式，自动使用所有可用线程 ({available_cores} 个核心)")
                else:
                    self.log("使用单线程模式")
                
                helios_root = self._get_helios_root()
                self.log(f"执行命令: {cmd}")
                self.log(f"工作目录: {helios_root}")
                
                process = subprocess.Popen(
                    cmd, 
                    shell=True, 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE,
                    text=True,
                    cwd=helios_root
                )
                
                # 实时输出日志
                while True:
                    output = process.stdout.readline()
                    if output == '' and process.poll() is not None:
                        break
                    if output:
                        self.log(output.strip())
                
                # 获取返回码
                return_code = process.poll()
                if return_code == 0:
                    self.log("Helios运行完成！")
                    self.log("您现在可以使用'合并LAS文件'功能来合并生成的点云文件。")
                    messagebox.showinfo("完成", "Helios运行完成！\n\n您现在可以使用'合并LAS文件'功能来合并生成的点云文件。")
                else:
                    stderr_output = process.stderr.read()
                    self.log(f"Helios运行失败，返回码: {return_code}")
                    self.log(f"错误信息: {stderr_output}")
                    messagebox.showerror("错误", f"Helios运行失败: {stderr_output}")
                    
            except Exception as e:
                self.log(f"运行Helios时出现错误: {e}")
                messagebox.showerror("错误", f"运行Helios时出现错误: {e}")
        
        # 在新线程中运行Helios
        thread = threading.Thread(target=run_helios_command)
        thread.daemon = True
        thread.start()
    
    def format_file_size(self, size_bytes):
        """格式化文件大小"""
        if size_bytes == 0:
            return "0 B"
        size_names = ["B", "KB", "MB", "GB"]
        i = 0
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024
            i += 1
        return f"{size_bytes:.1f} {size_names[i]}"
    
    def merge_las_files(self):
        """合并LAS文件"""
        if not HAS_LASPY:
            messagebox.showerror("错误", "缺少laspy库，请运行: pip install laspy")
            return
        
        def run_merge():
            try:
                # 询问用户选择文件还是文件夹
                choice = messagebox.askyesnocancel(
                    "选择输入方式",
                    "选择LAS文件输入方式：\n\n"
                    "是(Yes) - 选择单个文件\n"
                    "否(No) - 选择整个文件夹\n"
                    "取消(Cancel) - 取消操作"
                )
                
                if choice is None:  # 用户选择取消
                    self.log("用户取消了合并操作")
                    return
                
                las_files = []
                
                if choice:  # 用户选择"是" - 选择单个文件
                    # 选择要合并的LAS文件
                    selected_files = filedialog.askopenfilenames(
                        title="选择要合并的LAS文件",
                        filetypes=[
                            ("LAS文件", "*.las *.laz"),
                            ("所有文件", "*.*")
                        ],
                        initialdir=self.output_directory if self.output_directory else None
                    )
                    
                    if not selected_files:
                        self.log("未选择LAS文件")
                        return
                    
                    las_files = list(selected_files)
                    self.log(f"选择了 {len(las_files)} 个LAS文件")
                    
                else:  # 用户选择"否" - 选择文件夹
                    # 选择包含LAS文件的文件夹
                    folder = filedialog.askdirectory(
                        title="选择包含LAS文件的文件夹",
                        initialdir=self.output_directory if self.output_directory else None
                    )
                    
                    if not folder:
                        self.log("未选择文件夹")
                        return
                    
                    # 搜索文件夹中的所有LAS文件
                    self.log(f"搜索文件夹中的LAS文件: {folder}")
                    
                    # 查找所有LAS和LAZ文件（包括子文件夹）
                    for ext in ['*.las', '*.laz']:
                        las_files.extend(glob.glob(os.path.join(folder, '**', ext), recursive=True))
                    
                    # 去重并排序
                    las_files = sorted(list(set(las_files)))
                    
                    if not las_files:
                        self.log(f"在文件夹 {folder} 中未找到LAS文件")
                        messagebox.showwarning("警告", f"在选择的文件夹中未找到LAS文件")
                        return
                    
                    self.log(f"在文件夹中找到 {len(las_files)} 个LAS文件:")
                    for i, file_path in enumerate(las_files[:10]):  # 只显示前10个文件名
                        self.log(f"  {i+1}. {os.path.basename(file_path)}")
                    if len(las_files) > 10:
                        self.log(f"  ... 还有 {len(las_files) - 10} 个文件")
                
                if len(las_files) < 2:
                    messagebox.showwarning("警告", "需要至少两个LAS文件进行合并")
                    return
                
                # 生成默认输出文件名（尽量与OBJ/Survey同名）
                default_name = "merged"
                try:
                    ts_pattern = re.compile(r'^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}$')
                    if choice:
                        # 基于所选文件的父目录名推断；若父目录是时间戳，则回溯到父级（survey名）
                        first_file_dir = os.path.dirname(las_files[0])
                        base_dir = os.path.basename(first_file_dir)
                        if ts_pattern.match(base_dir):
                            default_name = os.path.basename(os.path.dirname(first_file_dir))
                        else:
                            default_name = base_dir
                    else:
                        # 基于所选文件夹名推断；若是时间戳目录则取父级
                        base_dir = os.path.basename(folder)
                        if ts_pattern.match(base_dir):
                            default_name = os.path.basename(os.path.dirname(folder))
                        else:
                            default_name = base_dir
                    if default_name.endswith('_las_output'):
                        default_name = default_name[:-11]
                    elif default_name.endswith('_output'):
                        default_name = default_name[:-7]
                except Exception:
                    pass

                # 选择输出文件
                initial_dir = None
                if self.merge_output_folder.get():
                    initial_dir = self.merge_output_folder.get()
                    self.log(f"使用指定的合并输出文件夹: {initial_dir}")
                elif self.output_directory:
                    initial_dir = self.output_directory
                
                output_file = filedialog.asksaveasfilename(
                    title="保存合并后的LAS文件",
                    defaultextension=".las",
                    filetypes=[("LAS文件", "*.las"), ("LAZ文件", "*.laz")],
                    initialdir=initial_dir,
                    initialfile=f"{default_name}.las"
                )
                
                if not output_file:
                    self.log("未选择输出文件")
                    return
                
                self.log(f"开始合并 {len(las_files)} 个LAS文件...")
                
                # 读取第一个文件作为模板
                self.log("读取第一个文件作为模板...")
                first_file = las_files[0]
                
                with laspy.open(first_file) as first_las:
                    # 创建输出文件的头部，基于第一个文件
                    output_header = first_las.header.copy()
                    
                    # 重置点数量，后面会更新
                    output_header.point_count = 0
                    output_header.number_of_point_records = 0
                
                # 创建输出文件
                with laspy.open(output_file, mode='w', header=output_header) as output_las:
                    total_points = 0
                    all_x, all_y, all_z = [], [], []
                    all_intensity = []
                    all_return_info = []
                    all_classifications = []
                    all_scan_angles = []
                    all_user_data = []
                    all_point_source_ids = []
                    all_colors = []
                    all_gps_times = []
                    
                    # 处理每个文件
                    for i, file_path in enumerate(las_files):
                        self.log(f"处理文件 {i+1}/{len(las_files)}: {os.path.basename(file_path)}")
                        
                        try:
                            with laspy.open(file_path) as las_file:
                                points = las_file.read()
                                file_point_count = len(points.x)
                                
                                # 添加基本坐标
                                all_x.extend(points.x)
                                all_y.extend(points.y)
                                all_z.extend(points.z)
                                
                                # 添加其他属性
                                if hasattr(points, 'intensity'):
                                    all_intensity.extend(points.intensity)
                                else:
                                    all_intensity.extend([0] * file_point_count)
                                
                                if hasattr(points, 'return_number'):
                                    all_return_info.extend(points.return_number)
                                else:
                                    all_return_info.extend([1] * file_point_count)
                                
                                if hasattr(points, 'classification'):
                                    all_classifications.extend(points.classification)
                                else:
                                    all_classifications.extend([0] * file_point_count)
                                
                                if hasattr(points, 'scan_angle_rank'):
                                    all_scan_angles.extend(points.scan_angle_rank)
                                else:
                                    all_scan_angles.extend([0] * file_point_count)
                                
                                if hasattr(points, 'user_data'):
                                    all_user_data.extend(points.user_data)
                                else:
                                    all_user_data.extend([0] * file_point_count)
                                
                                if hasattr(points, 'point_source_id'):
                                    all_point_source_ids.extend(points.point_source_id)
                                else:
                                    all_point_source_ids.extend([0] * file_point_count)
                                
                                # 颜色信息
                                if hasattr(points, 'red'):
                                    colors = list(zip(points.red, points.green, points.blue))
                                    all_colors.extend(colors)
                                else:
                                    all_colors.extend([(0, 0, 0)] * file_point_count)
                                
                                # GPS时间
                                if hasattr(points, 'gps_time'):
                                    all_gps_times.extend(points.gps_time)
                                else:
                                    all_gps_times.extend([0.0] * file_point_count)
                                
                                total_points += file_point_count
                                self.log(f"  添加了 {file_point_count:,} 个点")
                                
                        except Exception as e:
                            self.log(f"  处理文件时出错: {e}")
                            continue
                    
                    if total_points == 0:
                        self.log("没有成功读取任何点云数据")
                        messagebox.showerror("错误", "没有成功读取任何点云数据")
                        return
                    
                    # 写入合并后的数据
                    self.log("写入合并后的点云数据...")
                    
                    # 创建点记录
                    point_record = laspy.ScaleAwarePointRecord.zeros(
                        total_points, 
                        header=output_header
                    )
                    
                    # 设置基本坐标
                    point_record.x = np.array(all_x)
                    point_record.y = np.array(all_y)
                    point_record.z = np.array(all_z)
                    
                    # 设置其他属性
                    if hasattr(point_record, 'intensity'):
                        point_record.intensity = np.array(all_intensity, dtype=np.uint16)
                    
                    if hasattr(point_record, 'return_number'):
                        point_record.return_number = np.array(all_return_info, dtype=np.uint8)
                    
                    if hasattr(point_record, 'classification'):
                        point_record.classification = np.array(all_classifications, dtype=np.uint8)
                    
                    if hasattr(point_record, 'scan_angle_rank'):
                        point_record.scan_angle_rank = np.array(all_scan_angles, dtype=np.int8)
                    
                    if hasattr(point_record, 'user_data'):
                        point_record.user_data = np.array(all_user_data, dtype=np.uint8)
                    
                    if hasattr(point_record, 'point_source_id'):
                        point_record.point_source_id = np.array(all_point_source_ids, dtype=np.uint16)
                    
                    # 颜色信息
                    if all_colors and hasattr(point_record, 'red'):
                        colors_array = np.array(all_colors)
                        point_record.red = colors_array[:, 0].astype(np.uint16)
                        point_record.green = colors_array[:, 1].astype(np.uint16)
                        point_record.blue = colors_array[:, 2].astype(np.uint16)
                    
                    # GPS时间
                    if all_gps_times and hasattr(point_record, 'gps_time'):
                        point_record.gps_time = np.array(all_gps_times, dtype=np.float64)
                    
                    # 写入数据
                    output_las.write_points(point_record)
                    
                    # 更新头部信息
                    output_las.header.point_count = total_points
                    output_las.header.number_of_point_records = total_points
                    
                    # 更新边界框
                    output_las.header.x_min = float(np.min(all_x))
                    output_las.header.x_max = float(np.max(all_x))
                    output_las.header.y_min = float(np.min(all_y))
                    output_las.header.y_max = float(np.max(all_y))
                    output_las.header.z_min = float(np.min(all_z))
                    output_las.header.z_max = float(np.max(all_z))
                
                # 完成
                self.log(f"合并完成！")
                self.log(f"输出文件: {output_file}")
                self.log(f"总点数: {total_points:,}")
                self.log(f"文件大小: {self.format_file_size(os.path.getsize(output_file))}")
                
                messagebox.showinfo("成功", f"LAS文件合并完成！\n\n输出文件: {output_file}\n总点数: {total_points:,}")
                
            except Exception as e:
                self.log(f"合并失败: {e}")
                messagebox.showerror("错误", f"合并失败: {e}")
        
        # 在新线程中运行合并
        thread = threading.Thread(target=run_merge)
        thread.daemon = True
        thread.start()
    
    def run(self):
        """运行GUI"""
        self.root.mainloop()

if __name__ == "__main__":
    try:
        app = HeliosSceneGenerator()
        app.run()
    except Exception as e:
        print(f"启动程序时出错: {e}")
        import traceback
        traceback.print_exc()
        input("按Enter键退出...") 