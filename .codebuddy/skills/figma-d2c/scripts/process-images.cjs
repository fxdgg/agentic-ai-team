#!/usr/bin/env node

/**
 * 图片处理脚本
 * 批量压缩、转换 WebP、生成多分辨率版本
 *
 * 跨平台支持：macOS / Linux / Windows
 *
 * 用法：
 *   node process-images.cjs --dir src/assets/images
 *   node process-images.cjs --dir src/assets/images --quality 85 --webp
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');
const { IMAGE_CONFIG, PATHS } = require('./config.cjs');

// ─── 参数解析 ────────────────────────────────
const args = process.argv.slice(2);

function getArg(name, defaultValue) {
  const idx = args.indexOf(`--${name}`);
  if (idx === -1) return defaultValue;
  if (typeof defaultValue === 'boolean') return true;
  return args[idx + 1] || defaultValue;
}

const targetDir = path.resolve(getArg('dir', PATHS.images));
const quality = parseInt(getArg('quality', String(IMAGE_CONFIG.quality)), 10);
const generateWebP = getArg('webp', IMAGE_CONFIG.generateWebP);
const maxWidth = parseInt(getArg('max-width', String(IMAGE_CONFIG.maxWidth)), 10);
const dryRun = getArg('dry-run', false);

// ─── 工具函数 ────────────────────────────────
function formatBytes(bytes) {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

function getImageFiles(dir) {
  if (!fs.existsSync(dir)) {
    console.error(`❌ 目录不存在: ${dir}`);
    process.exit(1);
  }

  const files = [];
  const entries = fs.readdirSync(dir, { withFileTypes: true });

  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      files.push(...getImageFiles(fullPath));
    } else if (entry.isFile()) {
      const ext = path.extname(entry.name).toLowerCase();
      if (['.png', '.jpg', '.jpeg'].includes(ext)) {
        files.push(fullPath);
      }
    }
  }

  return files;
}

/**
 * 跨平台检查命令是否可用
 */
function checkTool(name) {
  try {
    const cmd = process.platform === 'win32' ? `where ${name}` : `command -v ${name}`;
    execSync(cmd, { stdio: 'pipe' });
    return true;
  } catch {
    return false;
  }
}

/**
 * 获取图片宽度（跨平台）
 * - macOS: sips
 * - Linux: identify (ImageMagick)
 * - Windows: 依赖 sharp（可选）
 */
function getImageWidth(filePath) {
  if (process.platform === 'darwin' && checkTool('sips')) {
    try {
      const info = execSync(`sips -g pixelWidth "${filePath}"`, { encoding: 'utf-8' });
      const match = info.match(/pixelWidth:\s*(\d+)/);
      return match ? parseInt(match[1], 10) : null;
    } catch {
      return null;
    }
  }

  if (checkTool('identify')) {
    try {
      const info = execSync(`identify -format "%w" "${filePath}"`, { encoding: 'utf-8' });
      return parseInt(info.trim(), 10) || null;
    } catch {
      return null;
    }
  }

  return null;
}

/**
 * 缩放图片宽度（跨平台）
 */
function resizeImage(filePath, targetWidth) {
  if (process.platform === 'darwin' && checkTool('sips')) {
    try {
      execSync(`sips --resampleWidth ${targetWidth} "${filePath}"`, { stdio: 'pipe' });
      return true;
    } catch {
      return false;
    }
  }

  if (checkTool('convert')) {
    try {
      execSync(`convert "${filePath}" -resize ${targetWidth}x "${filePath}"`, { stdio: 'pipe' });
      return true;
    } catch {
      return false;
    }
  }

  return false;
}

// ─── 主流程 ──────────────────────────────────
function main() {
  console.log('🖼️  D2C 图片处理工具');
  console.log('━'.repeat(50));
  console.log(`📂 目标目录: ${targetDir}`);
  console.log(`📊 压缩质量: ${quality}`);
  console.log(`🌐 生成 WebP: ${generateWebP ? '是' : '否'}`);
  console.log(`📏 最大宽度: ${maxWidth}px`);
  console.log(`💻 平台: ${process.platform}`);
  if (dryRun) console.log('⚡ 模拟运行模式（不实际修改文件）');
  console.log('━'.repeat(50));

  const files = getImageFiles(targetDir);

  if (files.length === 0) {
    console.log('📭 未找到可处理的图片文件');
    return;
  }

  console.log(`\n📋 找到 ${files.length} 个图片文件:\n`);

  let totalOriginal = 0;
  let totalProcessed = 0;

  const hasCwebp = checkTool('cwebp');

  if (generateWebP && !hasCwebp) {
    const installHint = process.platform === 'darwin'
      ? 'brew install webp'
      : process.platform === 'win32'
        ? '从 https://developers.google.com/speed/webp/download 下载安装'
        : 'sudo apt-get install webp  # 或 sudo yum install libwebp-tools';
    console.log(`⚠️  未安装 cwebp，跳过 WebP 生成。安装: ${installHint}\n`);
  }

  for (const file of files) {
    const relativePath = path.relative(PATHS.root, file);
    const originalSize = fs.statSync(file).size;
    totalOriginal += originalSize;

    console.log(`  📄 ${relativePath} (${formatBytes(originalSize)})`);

    if (dryRun) {
      totalProcessed += originalSize;
      continue;
    }

    // 检查宽度，超过最大宽度则缩放
    const currentWidth = getImageWidth(file);
    if (currentWidth && currentWidth > maxWidth) {
      if (resizeImage(file, maxWidth)) {
        console.log(`    ↳ 缩放: ${currentWidth}px → ${maxWidth}px`);
      } else {
        console.log(`    ⚠️ 缩放失败，无可用的图片处理工具（需要 sips/ImageMagick）`);
      }
    }

    // WebP 转换
    if (generateWebP && hasCwebp) {
      const webpPath = file.replace(/\.(png|jpg|jpeg)$/i, '.webp');
      try {
        execSync(`cwebp -q ${IMAGE_CONFIG.webpQuality} "${file}" -o "${webpPath}"`, { stdio: 'pipe' });
        const webpSize = fs.statSync(webpPath).size;
        const savings = ((1 - webpSize / originalSize) * 100).toFixed(1);
        console.log(`    ↳ WebP: ${formatBytes(webpSize)} (节省 ${savings}%)`);
      } catch (e) {
        console.log(`    ⚠️ WebP 转换失败: ${e.message}`);
      }
    }

    const newSize = fs.statSync(file).size;
    totalProcessed += newSize;
  }

  console.log('\n' + '━'.repeat(50));
  console.log('📊 处理结果汇总:');
  console.log(`   原始总大小: ${formatBytes(totalOriginal)}`);
  console.log(`   处理后大小: ${formatBytes(totalProcessed)}`);
  if (totalOriginal > totalProcessed) {
    const savings = ((1 - totalProcessed / totalOriginal) * 100).toFixed(1);
    console.log(`   节省空间:   ${formatBytes(totalOriginal - totalProcessed)} (${savings}%)`);
  }
  console.log('━'.repeat(50));
}

main();
