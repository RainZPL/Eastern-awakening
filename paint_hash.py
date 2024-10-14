import sys
import json
import zipfile
import os
import io
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QAction, QFileDialog, QColorDialog,
    QSlider, QLabel, QToolBar, QWidget, QMessageBox
)
from PyQt5.QtGui import QPainter, QPen, QImage, QColor
from PyQt5.QtCore import Qt, QPoint, QTime, QTimer
import requests
from web3 import Web3

# 连接到本地的 Ganache 节点，用于与智能合约交互
web3 = Web3(Web3.HTTPProvider('http://127.0.0.1:7545'))


# 全局 IPFS 节点地址，用户可以根据需要修改为远程节点或其他服务提供的 IPFS 网关
IPFS_NODE_ADDRESS = 'http://127.0.0.1:5001'


# 替换为在 Ganache 上部署的智能合约地址
contract_address = '0xB2cFcd4F6a26E11D87E343Ee158cB1da175Fe466'

# 合约的 ABI (Application Binary Interface)，定义了合约中可调用的函数和数据结构
contract_abi = '''
[
	{
		"inputs": [
			{
				"internalType": "string",
				"name": "_ipfsHash",
				"type": "string"
			}
		],
		"name": "storeIpfsHash",
		"outputs": [],
		"stateMutability": "nonpayable",
		"type": "function"
	},
	{
		"inputs": [],
		"name": "getIpfsHash",
		"outputs": [
			{
				"internalType": "string",
				"name": "",
				"type": "string"
			}
		],
		"stateMutability": "view",
		"type": "function"
	},
	{
		"inputs": [],
		"name": "ipfsHash",
		"outputs": [
			{
				"internalType": "string",
				"name": "",
				"type": "string"
			}
		],
		"stateMutability": "view",
		"type": "function"
	}
]
'''

# 定义绘图功能的类
class DrawingWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StaticContents)  # 设置窗口为静态内容
        self.myPenWidth = 2  # 设置默认画笔宽度
        self.eraserWidth = 10  # 橡皮擦宽度
        self.myPenColor = QColor(Qt.black)  # 设置默认颜色为黑色
        self.current_tool = 'pen'  # 设置默认工具为画笔
        self.image = QImage(self.size(), QImage.Format_RGB32)  # 创建一个空白的图像画布
        self.image.fill(Qt.white)  # 填充白色背景
        self.drawing = False  # 初始化绘图状态为 False
        self.lastPoint = QPoint()  # 保存上一个绘制点
        self.actions = []  # 用于存储绘图操作
        self.redo_stack = []  # 用于撤销操作的栈
        self.undo_stack = []  # 用于重做操作的栈
        self.timer = QTimer()  # 用于绘画回放的计时器
        self.replay_index = 0  # 回放时动作索引

    def set_pen_color(self, color):
        self.myPenColor = color  # 设置画笔颜色

    def set_pen_width(self, width):
        self.myPenWidth = width  # 设置画笔宽度

    def set_eraser_width(self, width):
        self.eraserWidth = width  # 设置橡皮擦宽度

    def set_tool(self, tool):
        self.current_tool = tool  # 设置当前使用的工具

    # 鼠标按下事件，用于记录开始绘制的起始点
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drawing = True
            self.lastPoint = event.pos()  # 获取当前鼠标位置
            action = {
                'action': 'start',
                'point': (self.lastPoint.x(), self.lastPoint.y()),
                'color': self.myPenColor.name() if self.current_tool == 'pen' else '#FFFFFF',
                'width': self.myPenWidth if self.current_tool == 'pen' else self.eraserWidth,
                'tool': self.current_tool,
            }
            self.actions.append(action)  # 保存起始动作
            self.redo_stack.clear()  # 清除重做栈

    # 鼠标移动事件，绘制连续的线条
    def mouseMoveEvent(self, event):
        if (event.buttons() & Qt.LeftButton) and self.drawing:
            painter = QPainter(self.image)  # 创建一个画家对象，用于在图像上绘制
            if self.current_tool == 'pen':  # 选择画笔
                pen = QPen(self.myPenColor, self.myPenWidth, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            elif self.current_tool == 'eraser':  # 选择橡皮擦
                pen = QPen(QColor(Qt.white), self.eraserWidth, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            painter.setPen(pen)
            painter.drawLine(self.lastPoint, event.pos())  # 画线
            self.lastPoint = event.pos()  # 更新最后一个点

            action = {'action': 'draw', 'point': (self.lastPoint.x(), self.lastPoint.y())}
            self.actions.append(action)  # 保存绘制动作
            self.update()  # 更新画布
            self.redo_stack.clear()  # 清除重做栈

    # 鼠标释放事件，表示结束当前绘制
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.drawing:
            self.drawing = False

    # 绘制事件，用于将图像显示在画布上
    def paintEvent(self, event):
        canvasPainter = QPainter(self)
        canvasPainter.drawImage(self.rect(), self.image, self.image.rect())  # 将图像绘制到界面上

    # 调整窗口大小时重绘
    def resizeEvent(self, event):
        if self.image.size() != self.size():
            newImage = QImage(self.size(), QImage.Format_RGB32)
            newImage.fill(Qt.white)  # 新图像填充白色
            painter = QPainter(newImage)
            painter.drawImage(QPoint(0, 0), self.image)  # 将原图像绘制到新的图像上
            self.image = newImage

    # 回放绘制过程
    def replay_actions(self):
        self.image.fill(Qt.white)  # 清空画布
        self.update()
        self.replay_index = 0  # 从头开始回放
        self.timer.timeout.connect(self.replay_step)
        self.timer.start(50)  # 每 50 毫秒回放一个动作

    def replay_step(self):
        if self.replay_index >= len(self.actions):  # 回放结束
            self.timer.stop()
            return

        action = self.actions[self.replay_index]
        if action['action'] == 'start':
            self.lastPoint = QPoint(*action['point'])
            self.myPenColor = QColor(action['color'])
            self.myPenWidth = action['width']
            self.eraserWidth = action['width']
            self.current_tool = action.get('tool', 'pen')
        elif action['action'] == 'draw':  # 绘制每一步动作
            painter = QPainter(self.image)
            if self.current_tool == 'pen':
                pen = QPen(self.myPenColor, self.myPenWidth, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            elif self.current_tool == 'eraser':
                pen = QPen(QColor(Qt.white), self.eraserWidth, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            painter.setPen(pen)
            currentPoint = QPoint(*action['point'])
            painter.drawLine(self.lastPoint, currentPoint)
            self.lastPoint = currentPoint
            self.update()
        self.replay_index += 1  # 更新回放索引

    # 撤销操作
    def undo(self):
        if not self.actions:
            return
        last_action = self.actions.pop()  # 从操作栈中移除最后一个动作
        self.redo_stack.append(last_action)  # 保存到重做栈
        if last_action['action'] == 'draw':
            while self.actions and self.actions[-1]['action'] == 'draw':
                self.redo_stack.append(self.actions.pop())  # 保存连续绘制的动作
        self.redraw_image()

    # 重做操作
    def redo(self):
        if not self.redo_stack:
            return
        action = self.redo_stack.pop()  # 从重做栈中恢复动作
        self.actions.append(action)
        if action['action'] == 'start':
            while self.redo_stack and self.redo_stack[-1]['action'] == 'draw':
                self.actions.append(self.redo_stack.pop())  # 恢复连续绘制的动作
        self.redraw_image()

    # 重绘整个画布
    def redraw_image(self):
        self.image.fill(Qt.white)  # 清空画布
        self.update()
        temp_actions = self.actions.copy()
        self.actions = []
        for action in temp_actions:
            if action['action'] == 'start':
                self.lastPoint = QPoint(*action['point'])
                self.myPenColor = QColor(action['color'])
                self.myPenWidth = action['width']
                self.eraserWidth = action['width']
                self.current_tool = action.get('tool', 'pen')
                self.actions.append(action)
            elif action['action'] == 'draw':
                painter = QPainter(self.image)
                if self.current_tool == 'pen':
                    pen = QPen(self.myPenColor, self.myPenWidth, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
                elif self.current_tool == 'eraser':
                    pen = QPen(QColor(Qt.white), self.eraserWidth, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
                painter.setPen(pen)
                currentPoint = QPoint(*action['point'])
                painter.drawLine(self.lastPoint, currentPoint)
                self.lastPoint = currentPoint
                self.update()
                self.actions.append(action)

    # 保存图像到 PNG 文件
    def save_image(self, file_path):
        self.image.save(file_path, "PNG")

    # 生成包含 JSON 和 PNG 图像的 ZIP 文件，存储在内存中
    def create_zip_file_in_memory(self, image_path):
        json_data = json.dumps({'actions': self.actions}, indent=4)  # 生成绘制动作的 JSON 数据

        # 创建一个内存中的 zip 文件
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, 'w') as zipf:
            # 写入 JSON 数据到 zip
            zipf.writestr("drawing_data.json", json_data)

            # 将本地 PNG 图像文件写入 zip
            with open(image_path, 'rb') as image_file:
                zipf.writestr("drawing_image.png", image_file.read())

        zip_buffer.seek(0)  # 重置缓冲区位置
        return zip_buffer

    # 上传 ZIP 文件到 IPFS
    def upload_to_ipfs(self, zip_buffer):
        try:
            files = {'file': zip_buffer.getvalue()}  # 读取内存中的 zip 文件
            response = requests.post(f'{IPFS_NODE_ADDRESS}/api/v0/add', files=files)  # 动态使用 IPFS 地址
            if response.status_code == 200:
                ipfs_hash = response.json()['Hash']
                print(f"文件已上传, IPFS 哈希: {ipfs_hash}")
                return ipfs_hash
            else:
                print(f"上传失败: {response.text}")
                return None
        except Exception as e:
            print(f"上传失败: {e}")
            return None

    # 导出图像并上传
    def export_and_upload(self, image_path):
        self.save_image(image_path)  # 保存 PNG 图像到本地
        zip_buffer = self.create_zip_file_in_memory(image_path)  # 创建 ZIP 文件
        ipfs_hash = self.upload_to_ipfs(zip_buffer)  # 上传到 IPFS

        if ipfs_hash:
            self.store_ipfs_in_contract(ipfs_hash)  # 将 IPFS 哈希存储到智能合约

    # 将 IPFS 哈希存储到智能合约
    def store_ipfs_in_contract(self, ipfs_hash):
        try:
            contract = web3.eth.contract(address=contract_address, abi=contract_abi)
            account = web3.eth.accounts[0]  # 使用 Ganache 上的第一个账户
            tx_hash = contract.functions.storeIpfsHash(ipfs_hash).transact({'from': account})
            web3.eth.wait_for_transaction_receipt(tx_hash)
            QMessageBox.information(self, "智能合约", "IPFS 哈希已存储到智能合约")
        except Exception as e:
            QMessageBox.warning(self, "智能合约", f"存储到智能合约失败: {e}")

# 定义主窗口类，包含工具栏、菜单栏等功能
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.drawing_widget = DrawingWidget()  # 创建绘图组件
        self.setCentralWidget(self.drawing_widget)
        self.initUI()

    # 初始化用户界面
    def initUI(self):
        self.setWindowTitle('绘图软件')
        self.setGeometry(100, 100, 800, 600)

        # 创建菜单栏
        menubar = self.menuBar()
        fileMenu = menubar.addMenu('文件')

        # 导出并上传的功能
        exportAction = QAction('导出并上传', self)
        exportAction.triggered.connect(self.export_and_upload)
        fileMenu.addAction(exportAction)

        # 回放绘画过程的功能
        replayAction = QAction('重放', self)
        replayAction.triggered.connect(self.drawing_widget.replay_actions)
        fileMenu.addAction(replayAction)

        # 撤销和重做的功能
        undoAction = QAction('撤销', self)
        undoAction.triggered.connect(self.drawing_widget.undo)
        fileMenu.addAction(undoAction)

        redoAction = QAction('重做', self)
        redoAction.triggered.connect(self.drawing_widget.redo)
        fileMenu.addAction(redoAction)

        # 创建工具栏
        toolbar = QToolBar("工具栏")
        self.addToolBar(toolbar)

        # 添加调色板按钮
        colorBtn = QAction('调色板', self)
        colorBtn.triggered.connect(self.choose_color)
        toolbar.addAction(colorBtn)

        # 笔宽调节滑块
        self.pen_slider_label = QLabel("笔宽:")
        self.pen_slider = QSlider(Qt.Horizontal)
        self.pen_slider.setMinimum(1)
        self.pen_slider.setMaximum(50)
        self.pen_slider.setValue(2)
        self.pen_slider.valueChanged.connect(self.change_pen_width)
        toolbar.addWidget(self.pen_slider_label)
        toolbar.addWidget(self.pen_slider)

        # 选择画笔和橡皮擦
        penBtn = QAction('画笔', self)
        penBtn.triggered.connect(self.select_pen)
        toolbar.addAction(penBtn)

        eraserBtn = QAction('橡皮擦', self)
        eraserBtn.triggered.connect(self.select_eraser)
        toolbar.addAction(eraserBtn)

    # 调色板功能，选择颜色
    def choose_color(self):
        color = QColorDialog.getColor()  # 打开调色板
        if color.isValid():
            self.drawing_widget.set_pen_color(color)  # 设置绘画颜色

    # 改变画笔宽度
    def change_pen_width(self, value):
        self.drawing_widget.set_pen_width(value)

    # 选择画笔工具
    def select_pen(self):
        self.drawing_widget.set_tool('pen')

    # 选择橡皮擦工具
    def select_eraser(self):
        self.drawing_widget.set_tool('eraser')

    # 导出并上传的操作
    def export_and_upload(self):
        options = QFileDialog.Options()
        image_path, _ = QFileDialog.getSaveFileName(self, "保存图像", "", "PNG Files (*.png)", options=options)
        if image_path:
            self.drawing_widget.export_and_upload(image_path)

# 主程序入口，启动 PyQt5 应用
if __name__ == '__main__':
    app = QApplication(sys.argv)
    mainWin = MainWindow()  # 创建主窗口
    mainWin.show()  # 显示窗口
    sys.exit(app.exec_())  # 进入主事件循环
