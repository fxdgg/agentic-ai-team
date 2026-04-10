/**
 * figma-data-filter.cjs
 *
 * Figma 原始节点树数据精简脚本
 *
 * 用途：在 @figma-analyzer Agent 通过 MCP get_figma_data 获取原始节点树后，
 * 执行此脚本过滤掉对 D2C 代码生成无用的节点和属性，大幅减少下游 Agent 的 token 消耗。
 *
 * 使用方式：
 *   node figma-data-filter.cjs <input.json> [output.json]
 *
 *   - input.json   : MCP 返回的原始 Figma 数据（JSON 文件路径）
 *   - output.json   : 过滤后的输出文件路径（可选，默认覆盖 input 同目录下 figma-data-filtered.json）
 *
 * 也可作为模块引入：
 *   const { filterFigmaData, filterNodeTree } = require('./figma-data-filter.cjs');
 *
 * 过滤规则：
 *   1. 移除不可见节点（visible: false）
 *   2. 移除辅助标注节点（名称匹配标注/参考线模式）
 *   3. 移除冗余默认属性值（opacity: 1, blendMode: NORMAL 等）
 *   4. 折叠单子节点的空容器包裹层
 *   5. 精简组件定义（仅保留被实例引用的组件变体）
 *   6. 裁剪超深嵌套的叶子节点（depth > maxDepth 时标记截断）
 *   7. 移除空 children 数组和空对象字段
 *   8. 精简 fills/effects/strokes 中的默认/无效项
 */

'use strict';

const fs = require('fs');
const path = require('path');

// ─── 配置常量 ─────────────────────────────────────────────────

/** 最大允许的节点嵌套深度，超过此深度的子树将被截断 */
const MAX_DEPTH = 12;

/** 辅助标注节点的名称匹配模式（正则） */
const ANNOTATION_PATTERNS = [
  /^_/,                          // 以下划线开头（设计师常用的标注前缀）
  /^#/,                          // 以 # 开头的标注节点
  /guideline/i,                  // 参考线
  /annotation/i,                 // 标注
  /redline/i,                    // 标注线
  /note/i,                       // 注释（但要排除 "footnote" 等合法节点）
  /^---/,                        // 分隔线标注
  /^\[.*\]$/,                    // [标注] 格式
  /specification/i,              // 规格标注
  /measurement/i,                // 尺寸标注
  /^\u6807\u6CE8/,               // "标注" 中文开头
  /^\u53C2\u8003/,               // "参考" 中文开头
];

/** 需要排除的 note 误匹配（包含这些词时不过滤） */
const NOTE_WHITELIST = ['footnote', 'notification', 'notable', 'notebook'];

/** 冗余默认属性：当值等于默认值时移除 */
const DEFAULT_PROPERTIES = {
  opacity: 1,
  blendMode: 'NORMAL',
  isMask: false,
  clipsContent: false,
  preserveRatio: false,
  locked: false,
  exportSettings: [],
};

/** 无信息量的节点类型（通常是设计稿中的辅助元素） */
const SKIP_NODE_TYPES = new Set([
  'SLICE',         // 切片（导出辅助，无视觉意义）
  'STICKY',        // 便签
  'STAMP',         // 印章
  'SHAPE_WITH_TEXT', // FigJam 形状
  'CONNECTOR',     // 连接线
  'CODE_BLOCK',    // 代码块（FigJam）
  'WIDGET',        // 小部件
  'EMBED',         // 嵌入内容
  'LINK_UNFURL',   // 链接预览
  'MEDIA',         // 媒体
]);

/** fills 中无效的类型 */
const SKIP_FILL_TYPES = new Set([
  'EMOJI',         // 表情符号填充
]);

// ─── 工具函数 ─────────────────────────────────────────────────

/**
 * 判断节点名是否匹配标注模式
 */
function isAnnotationNode(name) {
  if (!name || typeof name !== 'string') return false;
  const lower = name.toLowerCase();

  // note 特殊处理：排除白名单词
  for (const pattern of ANNOTATION_PATTERNS) {
    if (pattern.test(name)) {
      // 如果匹配的是 note 相关模式，检查白名单
      if (pattern.source.includes('note')) {
        if (NOTE_WHITELIST.some(w => lower.includes(w))) {
          return false;
        }
      }
      return true;
    }
  }
  return false;
}

/**
 * 移除对象中值为默认值的属性
 */
function removeDefaultProps(node) {
  for (const [key, defaultVal] of Object.entries(DEFAULT_PROPERTIES)) {
    if (node[key] === defaultVal) {
      delete node[key];
    }
    // 空数组也移除
    if (Array.isArray(defaultVal) && Array.isArray(node[key]) && node[key].length === 0) {
      delete node[key];
    }
  }
}

/**
 * 精简 fills 数组：移除不可见的填充和无效类型
 */
function filterFills(fills) {
  if (!Array.isArray(fills) || fills.length === 0) return undefined;

  const filtered = fills.filter(fill => {
    // 移除不可见填充
    if (fill.visible === false) return false;
    // 移除无效类型
    if (SKIP_FILL_TYPES.has(fill.type)) return false;
    // 移除完全透明的纯色填充
    if (fill.type === 'SOLID' && fill.color && fill.opacity === 0) return false;
    return true;
  });

  // 精简填充项内部：移除默认 opacity=1
  for (const fill of filtered) {
    if (fill.opacity === 1) delete fill.opacity;
    if (fill.visible === true) delete fill.visible;
    if (fill.blendMode === 'NORMAL') delete fill.blendMode;
  }

  return filtered.length > 0 ? filtered : undefined;
}

/**
 * 精简 effects 数组：移除不可见的效果
 */
function filterEffects(effects) {
  if (!Array.isArray(effects) || effects.length === 0) return undefined;

  const filtered = effects.filter(effect => {
    if (effect.visible === false) return false;
    return true;
  });

  // 精简效果项内部
  for (const effect of filtered) {
    if (effect.visible === true) delete effect.visible;
    if (effect.blendMode === 'NORMAL') delete effect.blendMode;
  }

  return filtered.length > 0 ? filtered : undefined;
}

/**
 * 精简 strokes 数组
 */
function filterStrokes(strokes) {
  if (!Array.isArray(strokes) || strokes.length === 0) return undefined;

  const filtered = strokes.filter(stroke => {
    if (stroke.visible === false) return false;
    return true;
  });

  for (const stroke of filtered) {
    if (stroke.opacity === 1) delete stroke.opacity;
    if (stroke.visible === true) delete stroke.visible;
    if (stroke.blendMode === 'NORMAL') delete stroke.blendMode;
  }

  return filtered.length > 0 ? filtered : undefined;
}

/**
 * 移除空值字段（null, undefined, 空字符串, 空数组, 空对象）
 */
function removeEmptyFields(obj) {
  if (!obj || typeof obj !== 'object') return obj;

  for (const key of Object.keys(obj)) {
    const val = obj[key];
    if (val === null || val === undefined || val === '') {
      delete obj[key];
    } else if (Array.isArray(val) && val.length === 0) {
      delete obj[key];
    } else if (typeof val === 'object' && !Array.isArray(val) && Object.keys(val).length === 0) {
      delete obj[key];
    }
  }
  return obj;
}

// ─── 核心过滤逻辑 ─────────────────────────────────────────────

/**
 * 收集所有被引用的组件 ID（通过 INSTANCE 节点的 componentId）
 */
function collectReferencedComponentIds(node, ids = new Set()) {
  if (!node) return ids;

  if (node.type === 'INSTANCE' && node.componentId) {
    ids.add(node.componentId);
  }

  if (Array.isArray(node.children)) {
    for (const child of node.children) {
      collectReferencedComponentIds(child, ids);
    }
  }

  return ids;
}

/**
 * 过滤单个节点及其子树
 *
 * @param {Object} node - Figma 节点对象
 * @param {number} depth - 当前嵌套深度
 * @param {Set<string>} referencedComponentIds - 被引用的组件 ID 集合
 * @param {Object} stats - 统计信息（引用传递）
 * @returns {Object|null} 过滤后的节点，null 表示该节点被过滤掉
 */
function filterNode(node, depth, referencedComponentIds, stats) {
  if (!node || typeof node !== 'object') return null;

  // ── 规则 1：移除不可见节点 ──
  if (node.visible === false) {
    stats.removedInvisible++;
    return null;
  }

  // ── 规则 2：移除跳过的节点类型 ──
  if (SKIP_NODE_TYPES.has(node.type)) {
    stats.removedByType++;
    return null;
  }

  // ── 规则 3：移除辅助标注节点 ──
  if (isAnnotationNode(node.name)) {
    stats.removedAnnotations++;
    return null;
  }

  // ── 规则 6：深度截断 ──
  if (depth > MAX_DEPTH) {
    stats.truncatedByDepth++;
    // 保留节点基本信息但截断子树
    return {
      id: node.id,
      name: node.name,
      type: node.type,
      _truncated: true,
      _originalChildCount: Array.isArray(node.children) ? node.children.length : 0,
    };
  }

  // ── 构造精简后的节点 ──
  const filtered = {};

  // 始终保留的核心属性
  const coreProps = ['id', 'name', 'type'];
  for (const prop of coreProps) {
    if (node[prop] !== undefined) {
      filtered[prop] = node[prop];
    }
  }

  // 布局属性（对 D2C 至关重要）
  const layoutProps = [
    'absoluteBoundingBox', 'absoluteRenderBounds', 'relativeTransform',
    'size', 'constraints', 'layoutMode', 'layoutAlign', 'layoutGrow',
    'primaryAxisSizingMode', 'counterAxisSizingMode',
    'primaryAxisAlignItems', 'counterAxisAlignItems',
    'paddingTop', 'paddingRight', 'paddingBottom', 'paddingLeft',
    'itemSpacing', 'counterAxisSpacing',
    'layoutPositioning', 'layoutWrap',
  ];
  for (const prop of layoutProps) {
    if (node[prop] !== undefined && node[prop] !== null) {
      filtered[prop] = node[prop];
    }
  }

  // 视觉属性（精简后）
  const filteredFills = filterFills(node.fills);
  if (filteredFills) filtered.fills = filteredFills;

  const filteredEffects = filterEffects(node.effects);
  if (filteredEffects) filtered.effects = filteredEffects;

  const filteredStrokes = filterStrokes(node.strokes);
  if (filteredStrokes) filtered.strokes = filteredStrokes;

  // 圆角（对还原重要）
  const cornerProps = ['cornerRadius', 'rectangleCornerRadii', 'topLeftRadius', 'topRightRadius', 'bottomLeftRadius', 'bottomRightRadius'];
  for (const prop of cornerProps) {
    if (node[prop] !== undefined && node[prop] !== null && node[prop] !== 0) {
      filtered[prop] = node[prop];
    }
  }

  // 文本属性（TEXT 节点的核心数据）
  if (node.type === 'TEXT') {
    const textProps = [
      'characters', 'style', 'characterStyleOverrides', 'styleOverrideTable',
      'textAutoResize', 'textAlignHorizontal', 'textAlignVertical',
      'paragraphSpacing', 'lineTypes', 'lineIndentations',
    ];
    for (const prop of textProps) {
      if (node[prop] !== undefined && node[prop] !== null) {
        filtered[prop] = node[prop];
      }
    }
  }

  // 组件相关属性
  if (node.type === 'INSTANCE') {
    const instanceProps = ['componentId', 'componentProperties', 'overrides'];
    for (const prop of instanceProps) {
      if (node[prop] !== undefined) {
        filtered[prop] = node[prop];
      }
    }
  }

  if (node.type === 'COMPONENT' || node.type === 'COMPONENT_SET') {
    // 规则 5：仅保留被引用的组件
    if (node.type === 'COMPONENT' && node.id && !referencedComponentIds.has(node.id)) {
      // 如果是 COMPONENT_SET 的子节点，还需检查是否被引用
      stats.removedUnusedComponents++;
      return null;
    }
    const componentProps = ['componentPropertyDefinitions', 'key', 'description'];
    for (const prop of componentProps) {
      if (node[prop] !== undefined) {
        filtered[prop] = node[prop];
      }
    }
  }

  // VECTOR / BOOLEAN 操作相关
  if (['VECTOR', 'BOOLEAN_OPERATION', 'STAR', 'LINE', 'ELLIPSE', 'REGULAR_POLYGON'].includes(node.type)) {
    // 对于矢量类型，保留 strokeWeight 和 strokeAlign
    if (node.strokeWeight !== undefined) filtered.strokeWeight = node.strokeWeight;
    if (node.strokeAlign !== undefined) filtered.strokeAlign = node.strokeAlign;
    // 不保留 fillGeometry / strokeGeometry（过大且代码生成不需要）
  }

  // 其他有用属性
  if (node.opacity !== undefined && node.opacity !== 1) {
    filtered.opacity = node.opacity;
  }
  if (node.blendMode && node.blendMode !== 'NORMAL') {
    filtered.blendMode = node.blendMode;
  }
  if (node.isMask === true) {
    filtered.isMask = true;
  }
  if (node.clipsContent === true) {
    filtered.clipsContent = true;
  }
  if (node.backgroundColor) {
    filtered.backgroundColor = node.backgroundColor;
  }

  // ── 规则 4 & 递归处理子节点 ──
  if (Array.isArray(node.children) && node.children.length > 0) {
    const filteredChildren = [];

    for (const child of node.children) {
      const filteredChild = filterNode(child, depth + 1, referencedComponentIds, stats);
      if (filteredChild) {
        filteredChildren.push(filteredChild);
      }
    }

    // 规则 4：折叠单子节点的空容器
    // 条件：当前节点是 FRAME/GROUP、无视觉属性、仅 1 个子节点
    if (
      filteredChildren.length === 1 &&
      (node.type === 'FRAME' || node.type === 'GROUP') &&
      !filtered.fills &&
      !filtered.effects &&
      !filtered.strokes &&
      !filtered.backgroundColor &&
      !filtered.cornerRadius &&
      !filtered.clipsContent &&
      !node.layoutMode  // 有 Auto Layout 的不折叠
    ) {
      stats.collapsedWrappers++;
      // 将子节点提升，但保留当前节点的布局信息（如果有的话）
      const child = filteredChildren[0];
      // 如果当前节点有 absoluteBoundingBox 但子节点没有，继承
      if (filtered.absoluteBoundingBox && !child.absoluteBoundingBox) {
        child.absoluteBoundingBox = filtered.absoluteBoundingBox;
      }
      child._collapsedFrom = filtered.name; // 标记折叠来源（调试用）
      return child;
    }

    if (filteredChildren.length > 0) {
      filtered.children = filteredChildren;
    }
  }

  // 移除剩余的默认属性和空字段
  removeDefaultProps(filtered);
  removeEmptyFields(filtered);

  stats.kept++;
  return filtered;
}

/**
 * 过滤完整的 Figma 节点树
 *
 * @param {Object} rawData - MCP get_figma_data 返回的原始数据
 * @returns {{ data: Object, stats: Object }} 过滤后的数据和统计信息
 */
function filterFigmaData(rawData) {
  const stats = {
    originalNodeCount: 0,
    kept: 0,
    removedInvisible: 0,
    removedByType: 0,
    removedAnnotations: 0,
    removedUnusedComponents: 0,
    truncatedByDepth: 0,
    collapsedWrappers: 0,
  };

  // 计算原始节点数
  function countNodes(node) {
    if (!node) return 0;
    let count = 1;
    if (Array.isArray(node.children)) {
      for (const child of node.children) {
        count += countNodes(child);
      }
    }
    return count;
  }

  // 查找根节点（MCP 返回格式可能不同）
  let rootNode = null;
  if (rawData.nodes) {
    // 格式 A：{ nodes: { "nodeId": { document: {...} } } }
    const nodeKeys = Object.keys(rawData.nodes);
    if (nodeKeys.length > 0) {
      const firstNode = rawData.nodes[nodeKeys[0]];
      rootNode = firstNode.document || firstNode;
    }
  } else if (rawData.document) {
    // 格式 B：{ document: {...} }
    rootNode = rawData.document;
  } else if (rawData.type) {
    // 格式 C：直接就是节点对象
    rootNode = rawData;
  }

  if (!rootNode) {
    console.error('❌ 无法识别 Figma 数据格式，返回原始数据');
    return { data: rawData, stats };
  }

  stats.originalNodeCount = countNodes(rootNode);

  // 收集被引用的组件 ID
  const referencedComponentIds = collectReferencedComponentIds(rootNode);

  // 执行过滤
  const filteredRoot = filterNode(rootNode, 0, referencedComponentIds, stats);

  // 重组输出数据（保留 metadata）
  const result = {};

  // 保留文件级 metadata（对组件映射有用）
  if (rawData.name) result.name = rawData.name;
  if (rawData.lastModified) result.lastModified = rawData.lastModified;
  if (rawData.version) result.version = rawData.version;

  // 保留组件注册表（仅保留被引用的组件）
  if (rawData.components) {
    const filteredComponents = {};
    for (const [id, comp] of Object.entries(rawData.components)) {
      if (referencedComponentIds.has(id)) {
        filteredComponents[id] = {
          name: comp.name,
          description: comp.description,
          // 移除 documentationLinks, remote 等非必要字段
        };
        if (comp.componentSetId) {
          filteredComponents[id].componentSetId = comp.componentSetId;
        }
      }
    }
    if (Object.keys(filteredComponents).length > 0) {
      result.components = filteredComponents;
    }
  }

  // 保留组件集信息（仅被引用的）
  if (rawData.componentSets) {
    const referencedSetIds = new Set();
    if (result.components) {
      for (const comp of Object.values(result.components)) {
        if (comp.componentSetId) referencedSetIds.add(comp.componentSetId);
      }
    }
    const filteredSets = {};
    for (const [id, set] of Object.entries(rawData.componentSets)) {
      if (referencedSetIds.has(id)) {
        filteredSets[id] = { name: set.name, description: set.description };
      }
    }
    if (Object.keys(filteredSets).length > 0) {
      result.componentSets = filteredSets;
    }
  }

  // 保留 styles（对 Token 映射有用）
  if (rawData.styles) {
    result.styles = rawData.styles;
  }

  // 放入过滤后的节点树
  result.document = filteredRoot;

  // 附加过滤统计（供 Agent 参考）
  result._filterStats = {
    ...stats,
    filteredNodeCount: stats.kept,
    reductionRate: stats.originalNodeCount > 0
      ? `${((1 - stats.kept / stats.originalNodeCount) * 100).toFixed(1)}%`
      : '0%',
    referencedComponents: referencedComponentIds.size,
  };

  return { data: result, stats };
}

/**
 * 仅过滤节点树（不处理 metadata），用于对已分片的子树执行过滤
 */
function filterNodeTree(nodeTree) {
  const stats = {
    originalNodeCount: 0,
    kept: 0,
    removedInvisible: 0,
    removedByType: 0,
    removedAnnotations: 0,
    removedUnusedComponents: 0,
    truncatedByDepth: 0,
    collapsedWrappers: 0,
  };

  const referencedComponentIds = collectReferencedComponentIds(nodeTree);
  const filtered = filterNode(nodeTree, 0, referencedComponentIds, stats);

  return { node: filtered, stats };
}

// ─── CLI 入口 ─────────────────────────────────────────────────

function main() {
  const args = process.argv.slice(2);

  if (args.length === 0) {
    console.log(`
Figma Data Filter - D2C 元数据精简工具

用法: node figma-data-filter.cjs <input.json> [output.json]

参数:
  input.json    MCP get_figma_data 返回的原始 JSON 文件
  output.json   过滤后的输出文件（默认: 同目录 figma-data-filtered.json）

示例:
  node figma-data-filter.cjs .d2c-temp/figma-data.json
  node figma-data-filter.cjs .d2c-temp/figma-data.json .d2c-temp/figma-data-filtered.json
    `);
    process.exit(0);
  }

  const inputPath = path.resolve(args[0]);
  const outputPath = args[1]
    ? path.resolve(args[1])
    : path.join(path.dirname(inputPath), 'figma-data-filtered.json');

  // 读取输入
  if (!fs.existsSync(inputPath)) {
    console.error(`❌ 输入文件不存在: ${inputPath}`);
    process.exit(1);
  }

  console.log(`📖 读取原始数据: ${inputPath}`);
  const rawContent = fs.readFileSync(inputPath, 'utf-8');
  let rawData;
  try {
    rawData = JSON.parse(rawContent);
  } catch (e) {
    console.error(`❌ JSON 解析失败: ${e.message}`);
    process.exit(1);
  }

  const rawSize = Buffer.byteLength(rawContent, 'utf-8');
  console.log(`📊 原始数据大小: ${(rawSize / 1024).toFixed(1)} KB`);

  // 执行过滤
  console.log(`🔧 执行数据精简...`);
  const { data, stats } = filterFigmaData(rawData);

  // 写入输出
  const outputContent = JSON.stringify(data, null, 2);
  const outputSize = Buffer.byteLength(outputContent, 'utf-8');
  fs.writeFileSync(outputPath, outputContent, 'utf-8');

  // 输出统计
  console.log(`\n✅ 精简完成！`);
  console.log(`─────────────────────────────────────`);
  console.log(`📊 过滤统计:`);
  console.log(`   原始节点数:       ${stats.originalNodeCount}`);
  console.log(`   保留节点数:       ${stats.kept}`);
  console.log(`   移除-不可见:      ${stats.removedInvisible}`);
  console.log(`   移除-类型跳过:    ${stats.removedByType}`);
  console.log(`   移除-标注节点:    ${stats.removedAnnotations}`);
  console.log(`   移除-未引用组件:  ${stats.removedUnusedComponents}`);
  console.log(`   截断-超深嵌套:    ${stats.truncatedByDepth}`);
  console.log(`   折叠-空容器:      ${stats.collapsedWrappers}`);
  console.log(`─────────────────────────────────────`);
  console.log(`   数据大小: ${(rawSize / 1024).toFixed(1)} KB → ${(outputSize / 1024).toFixed(1)} KB (${((1 - outputSize / rawSize) * 100).toFixed(1)}% 减少)`);
  console.log(`   节点精简率: ${data._filterStats?.reductionRate || 'N/A'}`);
  console.log(`─────────────────────────────────────`);
  console.log(`📁 输出文件: ${outputPath}`);
}

// ─── 模块导出 ─────────────────────────────────────────────────

module.exports = {
  filterFigmaData,
  filterNodeTree,
  filterNode,
  isAnnotationNode,
  MAX_DEPTH,
  ANNOTATION_PATTERNS,
  SKIP_NODE_TYPES,
};

// CLI 模式执行
if (require.main === module) {
  main();
}
