# Paint Hash Demo

## 项目简介

该项目是一个 **Paint Hash** 示例，用于绘制和上传图片、生成与存储 IPFS 哈希值的 demo。虽然项目中提供了一个可执行文件 **`paint_hash.exe`**，但是由于它只是一个演示版本，**不适合直接用于上传到智能合约**。若想进行合约交互和上传图片，建议下载源代码 **`paint_hash.py`** 并按照说明进行操作。

## 功能说明

- **绘图功能**：用户可以使用调色板绘制不同颜色、线条粗细的图画。
- **撤销与重做**：支持撤销与重做绘图操作。
- **回放功能**：可以回放绘画过程。
- **调色板**：支持选择和更改绘画颜色。
- **IPFS 上传**：在绘图完成后，作品会上传到 IPFS，返回作品的 IPFS 哈希。
- **合约交互**：演示版本的合约上传不适合使用，建议通过源文件进行合约交互。

## 注意事项

1. **`paint_hash.exe`** 是演示版本，主要功能演示包括绘画与IPFS上传功能。
2. 如果需要进行合约交互和实际上传，请使用源文件 **`paint_hash.py`**，并按照下文安装所需库与调整参数。
3. **不要直接使用 `paint_hash.exe` 上传到区块链智能合约**。由于合约交互功能并未在该版本中完全实现或优化，因此只能作为功能演示。

## 安装和使用步骤

### 1. 克隆项目

```bash
git clone https://github.com/RainZPL/Eastern-awakening.git
cd Eastern-awakening
```

### 2. 安装依赖库
运行 **`paint_hash.py`** 需要安装以下 Python 库：

```bash
pip install PyQt5
pip install web3
pip install ipfshttpclient
pip install requests
```

### 3. 修改参数
在使用前，请务必修改以下代码中的相关参数：

- **IPFS 配置**：IPFS 节点的本地或远程地址。
- **合约地址和 ABI**：在合约交互时，请确保正确填写合约地址和 ABI。

在 **`paint_hash.py`** 文件中，查找以下部分代码并根据您的配置进行修改：

```python
# Web3 连接配置（默认是 Ganache 或其他本地节点）
web3 = Web3(Web3.HTTPProvider('http://127.0.0.1:7545'))

# 替换为 IPFS 节点的地址（可以是本地节点或者远程 IPFS 网关）
IPFS_NODE_ADDRESS = 'http://127.0.0.1:5001'  # 默认是本地运行的 IPFS 节点

# 替换为部署的合约地址
contract_address = 'YOUR_CONTRACT_ADDRESS'

# 替换为合约的 ABI
contract_abi = '''
[{"inputs": [...], "name": "storeIpfsHash", "outputs": [], ...}]
'''
```

### 4. 运行

运行以下命令启动应用：

```bash
python paint_hash.py
```

启动应用后，您可以在应用中进行绘画，点击 “导出并上传” 按钮将图像上传至 IPFS，并将哈希存储到合约（如果配置了合约地址和 ABI）。
