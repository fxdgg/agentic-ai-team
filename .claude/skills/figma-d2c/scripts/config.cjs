/**
 * D2C Skill 核心配置
 * 路径、域名、技术栈、资源处理等全局配置
 *
 * 技术栈配置支持自动检测：脚本会尝试读取项目 package.json，
 * 根据依赖自动推断 framework / componentLibrary / iconLibrary 等字段。
 * 也可手动在 TECH_STACK 中覆盖。
 */

const path = require('path');
const fs = require('fs');

// ─── 项目路径配置 ──────────────────────────────
const PROJECT_ROOT = path.resolve(__dirname, '../../../../');

/**
 * 尝试读取项目 package.json 的 dependencies + devDependencies
 */
function readProjectDeps() {
  const pkgPath = path.join(PROJECT_ROOT, 'package.json');
  if (!fs.existsSync(pkgPath)) return {};
  try {
    const pkg = JSON.parse(fs.readFileSync(pkgPath, 'utf-8'));
    return { ...pkg.dependencies, ...pkg.devDependencies };
  } catch {
    return {};
  }
}

/**
 * 从 package.json 推断技术栈
 */
function detectTechStack() {
  const deps = readProjectDeps();
  const has = (name) => !!deps[name];

  // --- Framework ---
  let framework = 'react';
  if (has('vue') || has('nuxt')) framework = 'vue';
  else if (has('@angular/core')) framework = 'angular';

  // --- Language ---
  const language = has('typescript') || has('vue-tsc') ? 'typescript' : 'javascript';
  const fileExtension = framework === 'vue' ? '.vue' : language === 'typescript' ? '.tsx' : '.jsx';

  // --- Component Library ---
  let componentLibrary = '';
  let componentVersion = '';
  const libMap = {
    'tdesign-react': 'tdesign-react',
    'tdesign-vue-next': 'tdesign-vue-next',
    'antd': 'antd',
    'ant-design-vue': 'ant-design-vue',
    'element-plus': 'element-plus',
    '@arco-design/web-react': '@arco-design/web-react',
    '@arco-design/web-vue': '@arco-design/web-vue',
  };
  for (const [pkg, name] of Object.entries(libMap)) {
    if (has(pkg)) {
      componentLibrary = name;
      componentVersion = (deps[pkg] || '').replace(/[\^~>=<]/g, '');
      break;
    }
  }

  // --- Icon Library ---
  let iconLibrary = '';
  let iconVersion = '';
  const iconMap = {
    'tdesign-icons-react': 'tdesign-icons-react',
    'tdesign-icons-vue-next': 'tdesign-icons-vue-next',
    '@ant-design/icons': '@ant-design/icons',
    '@ant-design/icons-vue': '@ant-design/icons-vue',
    'lucide-react': 'lucide-react',
    'lucide-vue-next': 'lucide-vue-next',
    '@iconify/vue': '@iconify/vue',
    '@iconify/react': '@iconify/react',
  };
  for (const [pkg, name] of Object.entries(iconMap)) {
    if (has(pkg)) {
      iconLibrary = name;
      iconVersion = (deps[pkg] || '').replace(/[\^~>=<]/g, '');
      break;
    }
  }

  // --- Styling ---
  let styling = 'css';
  if (has('tailwindcss')) styling = 'tailwindcss';
  else if (has('sass') || has('node-sass')) styling = 'scss';
  else if (has('less')) styling = 'less';
  else if (has('styled-components')) styling = 'styled-components';
  else if (has('@emotion/react') || has('@emotion/styled')) styling = 'emotion';

  // --- Build Tool ---
  let buildTool = '';
  if (has('vite')) buildTool = 'vite';
  else if (has('next')) buildTool = 'next';
  else if (has('nuxt')) buildTool = 'nuxt';
  else if (has('webpack')) buildTool = 'webpack';

  return {
    framework,
    language,
    styling,
    componentLibrary,
    componentVersion,
    iconLibrary,
    iconVersion,
    fileExtension,
    buildTool,
  };
}

// ─── 自动检测技术栈（可手动覆盖） ───────────────
const TECH_STACK = detectTechStack();

// ─── 路径配置（根据框架自适应） ──────────────────
function detectPaths() {
  const pagesDir = fs.existsSync(path.join(PROJECT_ROOT, 'src/views'))
    ? path.join(PROJECT_ROOT, 'src/views')
    : fs.existsSync(path.join(PROJECT_ROOT, 'src/pages'))
      ? path.join(PROJECT_ROOT, 'src/pages')
      : fs.existsSync(path.join(PROJECT_ROOT, 'app'))
        ? path.join(PROJECT_ROOT, 'app')
        : path.join(PROJECT_ROOT, 'src/pages');

  const hooksDir = TECH_STACK.framework === 'vue'
    ? (fs.existsSync(path.join(PROJECT_ROOT, 'src/composables'))
        ? path.join(PROJECT_ROOT, 'src/composables')
        : path.join(PROJECT_ROOT, 'src/composables'))
    : path.join(PROJECT_ROOT, 'src/hooks');

  const servicesDir = TECH_STACK.framework === 'vue'
    ? (fs.existsSync(path.join(PROJECT_ROOT, 'src/api'))
        ? path.join(PROJECT_ROOT, 'src/api')
        : path.join(PROJECT_ROOT, 'src/services'))
    : path.join(PROJECT_ROOT, 'src/services');

  return {
    root: PROJECT_ROOT,
    components: path.join(PROJECT_ROOT, 'src/components'),
    pages: pagesDir,
    images: path.join(PROJECT_ROOT, 'src/assets/images'),
    icons: path.join(PROJECT_ROOT, 'src/assets/icons'),
    types: path.join(PROJECT_ROOT, 'src/types'),
    hooks: hooksDir,
    services: servicesDir,
    temp: path.join(PROJECT_ROOT, '.d2c-temp'),
    vrtScreenshots: path.join(PROJECT_ROOT, '.d2c-temp/vrt'),
  };
}

const PATHS = detectPaths();

// ─── CDN / 域名配置 ─────────────────────────
const CDN = {
  /** 图片 CDN 域名（按需配置） */
  imageDomain: process.env.D2C_CDN_DOMAIN || '',
  /** 图片 CDN 上传路径前缀 */
  imagePrefix: process.env.D2C_CDN_PREFIX || '/assets/images/',
  /** 是否启用 CDN 上传 */
  enabled: !!process.env.D2C_CDN_DOMAIN,
};

// ─── Figma 访问配置 ─────────────────────────
const FIGMA = {
  /**
   * Figma Personal Access Token (PAT)
   * ⚠️ 安全提示：切勿将 Token 硬编码在代码中！
   * 推荐通过以下方式注入：
   *   - 本地开发：在 .env.local 中设置 FIGMA_ACCESS_TOKEN=figd_xxx（已加入 .gitignore）
   *   - CI/CD：通过 Pipeline Variables 或 Secrets Manager 注入
   */
  accessToken: process.env.FIGMA_ACCESS_TOKEN || '',
  /** Figma API 基础 URL */
  apiBase: 'https://api.figma.com/v1',
  /** 是否已配置有效 Token */
  isConfigured: !!process.env.FIGMA_ACCESS_TOKEN,
};

// ─── 图片处理配置 ─────────────────────────────
const IMAGE_CONFIG = {
  /** Figma 导出 PNG 的缩放比例（2 = @2x） */
  pngScale: 2,
  /** 图片压缩质量 (0-100) */
  quality: 85,
  /** 是否生成 WebP 格式 */
  generateWebP: true,
  /** WebP 质量 */
  webpQuality: 80,
  /** 最大宽度（超过则缩放） */
  maxWidth: 2400,
  /** 支持的图片格式 */
  supportedFormats: ['.png', '.jpg', '.jpeg', '.svg', '.webp', '.gif'],
  /** 需要生成的分辨率倍率 */
  resolutions: [1, 2],
};

// ─── SVG 优化配置 ─────────────────────────────
const SVG_CONFIG = {
  /** SVGO 优化插件配置 */
  svgoPlugins: [
    'removeDoctype',
    'removeXMLProcInst',
    'removeComments',
    'removeMetadata',
    'removeEditorsNSData',
    'cleanupAttrs',
    'mergeStyles',
    'inlineStyles',
    'minifyStyles',
    'removeUselessDefs',
    'cleanupNumericValues',
    'convertColors',
    'removeUnknownsAndDefaults',
    'removeNonInheritableGroupAttrs',
    'removeUselessStrokeAndFill',
    // 注意：不移除 viewBox，SVG 图标需要 viewBox 来正确缩放
    // 'removeViewBox',
    'cleanupEnableBackground',
    'removeHiddenElems',
    'removeEmptyText',
    'convertShapeToPath',
    'convertEllipseToCircle',
    'moveElemsAttrsToGroup',
    'moveGroupAttrsToElems',
    'collapseGroups',
    'convertPathData',
    'convertTransform',
    'removeEmptyAttrs',
    'removeEmptyContainers',
    'mergePaths',
    'removeUnusedNS',
    'sortDefsChildren',
    'removeTitle',
    'removeDesc',
  ],
};

// ─── VRT（视觉回归测试）配置 ─────────────────
const VRT_CONFIG = {
  /** 视口宽度 */
  viewportWidth: 1440,
  /** 视口高度 */
  viewportHeight: 900,
  /** 差异阈值（0-1，越小越严格） */
  threshold: 0.05,
  /** 截图格式 */
  format: 'png',
};

// ─── 代码生成配置 ─────────────────────────────
const CODE_CONFIG = {
  /** 单文件最大行数 */
  maxLinesPerFile: 300,
  /** 缩进方式 */
  indent: 2,
  /** 引号风格 */
  quotes: 'single',
  /** 分号 */
  semi: true,
  /** 尾随逗号 */
  trailingComma: 'all',
};

// ─── v5.0 锁定配置文件路径 ────────────────────
const CONTRACT_FILES = {
  requestTemplate: path.join(__dirname, '../request-template.json'),
  projectProfile: path.join(__dirname, '../project-profile.json'),
  componentMap: path.join(__dirname, '../component-map.json'),
  tokenAliases: path.join(__dirname, '../token-aliases.json'),
  manifestTemplate: path.join(__dirname, '../generation-manifest.template.json'),
};

module.exports = {
  PATHS,
  CDN,
  FIGMA,
  TECH_STACK,
  IMAGE_CONFIG,
  SVG_CONFIG,
  VRT_CONFIG,
  CODE_CONFIG,
  CONTRACT_FILES,
};
