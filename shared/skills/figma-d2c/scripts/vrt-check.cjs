#!/usr/bin/env node

/**
 * 视觉回归对比工具（VRT - Visual Regression Testing）
 * 对比 Figma 设计稿截图与本地运行页面截图，检测视觉差异
 *
 * 跨平台支持：macOS / Linux / Windows
 * 截图方式：优先使用 Playwright（跨平台），回退到系统截图工具
 *
 * 用法：
 *   node vrt-check.cjs --figma-image design.png --url http://localhost:5173
 *   node vrt-check.cjs --figma-image design.png --local-image screenshot.png
 *   node vrt-check.cjs --compare-dir .d2c-temp/vrt
 *
 * 依赖（可选）：
 *   npm install -D pixelmatch pngjs
 *   npm install -D playwright（用于自动截图）
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');
const { VRT_CONFIG, PATHS } = require('./config.cjs');

// ─── 参数解析 ────────────────────────────────
const args = process.argv.slice(2);

function getArg(name, defaultValue) {
  const idx = args.indexOf(`--${name}`);
  if (idx === -1) return defaultValue;
  if (typeof defaultValue === 'boolean') return true;
  return args[idx + 1] || defaultValue;
}

const figmaImage = getArg('figma-image', '');
const localImage = getArg('local-image', '');
const targetUrl = getArg('url', '');
const compareDir = getArg('compare-dir', '');
const threshold = parseFloat(getArg('threshold', String(VRT_CONFIG.threshold)));

// ─── 工具函数 ────────────────────────────────
function ensureDir(dir) {
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
}

function checkDependency(name) {
  try {
    require.resolve(name);
    return true;
  } catch {
    return false;
  }
}

/**
 * 使用像素级对比计算差异
 * 需要安装 pixelmatch + pngjs
 */
function pixelCompare(img1Path, img2Path, diffOutputPath) {
  if (!checkDependency('pixelmatch') || !checkDependency('pngjs')) {
    console.log('⚠️  像素级对比需要安装依赖:');
    console.log('   npm install -D pixelmatch pngjs\n');
    return null;
  }

  const pixelmatch = require('pixelmatch');
  const { PNG } = require('pngjs');

  const img1 = PNG.sync.read(fs.readFileSync(img1Path));
  const img2 = PNG.sync.read(fs.readFileSync(img2Path));

  // 尺寸对齐（取较大值）
  const width = Math.max(img1.width, img2.width);
  const height = Math.max(img1.height, img2.height);

  // 创建统一尺寸的 buffer
  const normalizedImg1 = new Uint8Array(width * height * 4);
  const normalizedImg2 = new Uint8Array(width * height * 4);

  // 复制数据（多余区域保持透明）
  for (let y = 0; y < img1.height; y++) {
    for (let x = 0; x < img1.width; x++) {
      const srcIdx = (y * img1.width + x) * 4;
      const dstIdx = (y * width + x) * 4;
      normalizedImg1[dstIdx] = img1.data[srcIdx];
      normalizedImg1[dstIdx + 1] = img1.data[srcIdx + 1];
      normalizedImg1[dstIdx + 2] = img1.data[srcIdx + 2];
      normalizedImg1[dstIdx + 3] = img1.data[srcIdx + 3];
    }
  }

  for (let y = 0; y < img2.height; y++) {
    for (let x = 0; x < img2.width; x++) {
      const srcIdx = (y * img2.width + x) * 4;
      const dstIdx = (y * width + x) * 4;
      normalizedImg2[dstIdx] = img2.data[srcIdx];
      normalizedImg2[dstIdx + 1] = img2.data[srcIdx + 1];
      normalizedImg2[dstIdx + 2] = img2.data[srcIdx + 2];
      normalizedImg2[dstIdx + 3] = img2.data[srcIdx + 3];
    }
  }

  const diff = new PNG({ width, height });

  const mismatchCount = pixelmatch(
    normalizedImg1,
    normalizedImg2,
    diff.data,
    width,
    height,
    { threshold: 0.1 }
  );

  // 保存差异图
  if (diffOutputPath) {
    fs.writeFileSync(diffOutputPath, PNG.sync.write(diff));
  }

  const totalPixels = width * height;
  const diffPercentage = (mismatchCount / totalPixels) * 100;

  return {
    width,
    height,
    totalPixels,
    mismatchCount,
    diffPercentage,
    passed: diffPercentage <= threshold * 100,
  };
}

/**
 * 跨平台截图
 * 优先使用 Playwright（跨平台），回退到系统工具
 */
async function captureScreenshot(outputPath, url) {
  // 方式一：Playwright（跨平台推荐）
  if (checkDependency('playwright')) {
    try {
      const { chromium } = require('playwright');
      const browser = await chromium.launch();
      const page = await browser.newPage({
        viewport: { width: VRT_CONFIG.viewportWidth, height: VRT_CONFIG.viewportHeight },
      });
      if (url) await page.goto(url, { waitUntil: 'networkidle' });
      await page.screenshot({ path: outputPath, fullPage: false });
      await browser.close();
      console.log(`📸 Playwright 截图完成: ${path.basename(outputPath)}`);
      return true;
    } catch (e) {
      console.log(`⚠️  Playwright 截图失败: ${e.message}`);
    }
  }

  // 方式二：macOS screencapture（交互式）
  if (process.platform === 'darwin') {
    console.log('📸 请在 3 秒内切换到浏览器窗口并选择截图区域...');
    try {
      execSync(`screencapture -i "${outputPath}"`, { stdio: 'inherit' });
      return fs.existsSync(outputPath);
    } catch {
      console.log('⚠️  截图取消或失败');
    }
  }

  // 方式三：Linux gnome-screenshot / scrot
  if (process.platform === 'linux') {
    const tools = ['gnome-screenshot', 'scrot'];
    for (const tool of tools) {
      try {
        execSync(`command -v ${tool}`, { stdio: 'pipe' });
        const cmd = tool === 'gnome-screenshot'
          ? `gnome-screenshot -f "${outputPath}"`
          : `scrot "${outputPath}"`;
        execSync(cmd, { stdio: 'pipe' });
        if (fs.existsSync(outputPath)) {
          console.log(`📸 ${tool} 截图完成`);
          return true;
        }
      } catch {
        continue;
      }
    }
  }

  console.log('⚠️  无法自动截图。推荐安装 Playwright: npm install -D playwright');
  console.log('   然后运行: npx playwright install chromium');
  return false;
}

// ─── 基础文件信息对比 ─────────────────────────
function basicCompare(img1Path, img2Path) {
  const stat1 = fs.statSync(img1Path);
  const stat2 = fs.statSync(img2Path);

  console.log('\n📊 文件信息对比:');
  console.log(`   设计稿: ${path.basename(img1Path)} (${(stat1.size / 1024).toFixed(1)} KB)`);
  console.log(`   截图:   ${path.basename(img2Path)} (${(stat2.size / 1024).toFixed(1)} KB)`);
  console.log(`   大小差异: ${Math.abs(stat1.size - stat2.size)} bytes`);
}

// ─── 批量对比模式 ─────────────────────────────
function batchCompare(dir) {
  if (!fs.existsSync(dir)) {
    console.error(`❌ 目录不存在: ${dir}`);
    process.exit(1);
  }

  const files = fs.readdirSync(dir);
  const figmaFiles = files.filter((f) => f.startsWith('figma-') && f.endsWith('.png'));
  const localFiles = files.filter((f) => f.startsWith('local-') && f.endsWith('.png'));

  if (figmaFiles.length === 0) {
    console.log('📭 未找到 figma-*.png 文件');
    return;
  }

  console.log(`\n📋 找到 ${figmaFiles.length} 组对比:\n`);

  let passCount = 0;
  let failCount = 0;

  for (const figmaFile of figmaFiles) {
    const name = figmaFile.replace('figma-', '');
    const localFile = `local-${name}`;

    if (!localFiles.includes(localFile)) {
      console.log(`  ⏭️  ${name} — 缺少本地截图，跳过`);
      continue;
    }

    const figmaPath = path.join(dir, figmaFile);
    const localPath = path.join(dir, localFile);
    const diffPath = path.join(dir, `diff-${name}`);

    const result = pixelCompare(figmaPath, localPath, diffPath);

    if (result) {
      const icon = result.passed ? '✅' : '❌';
      console.log(`  ${icon} ${name} — 差异: ${result.diffPercentage.toFixed(2)}% (阈值: ${threshold * 100}%)`);
      if (result.passed) passCount++;
      else failCount++;
    } else {
      basicCompare(figmaPath, localPath);
    }
  }

  console.log('\n' + '━'.repeat(50));
  console.log(`📊 结果: ${passCount} 通过, ${failCount} 不通过`);
}

// ─── 主流程 ──────────────────────────────────
async function main() {
  console.log('🔍 D2C 视觉回归对比工具');
  console.log('━'.repeat(50));

  ensureDir(PATHS.vrtScreenshots);

  // 批量对比模式
  if (compareDir) {
    batchCompare(compareDir);
    return;
  }

  // 单图对比模式
  if (!figmaImage) {
    console.log('用法:');
    console.log('  单图对比:');
    console.log('    node vrt-check.cjs --figma-image design.png --local-image screenshot.png');
    console.log('    node vrt-check.cjs --figma-image design.png --url http://localhost:5173');
    console.log('');
    console.log('  批量对比:');
    console.log('    node vrt-check.cjs --compare-dir .d2c-temp/vrt');
    console.log('');
    console.log('  文件命名规则（批量模式）:');
    console.log('    figma-<name>.png — 设计稿截图');
    console.log('    local-<name>.png — 本地截图');
    console.log('    diff-<name>.png  — 差异图（自动生成）');
    return;
  }

  if (!fs.existsSync(figmaImage)) {
    console.error(`❌ 设计稿图片不存在: ${figmaImage}`);
    process.exit(1);
  }

  let screenshotPath = localImage;

  // 如果提供了 URL 但没有截图，尝试截取
  if (!screenshotPath && targetUrl) {
    screenshotPath = path.join(PATHS.vrtScreenshots, 'local-screenshot.png');
    console.log(`🌐 目标 URL: ${targetUrl}`);

    const success = await captureScreenshot(screenshotPath, targetUrl);
    if (!success) {
      console.error('❌ 未获取到截图');
      process.exit(1);
    }
  }

  if (!screenshotPath || !fs.existsSync(screenshotPath)) {
    console.error('❌ 请提供 --local-image 或 --url 参数');
    process.exit(1);
  }

  const diffPath = path.join(PATHS.vrtScreenshots, 'diff-result.png');
  const result = pixelCompare(figmaImage, screenshotPath, diffPath);

  if (result) {
    console.log('\n📊 像素级对比结果:');
    console.log(`   画布尺寸:  ${result.width} × ${result.height}`);
    console.log(`   总像素:    ${result.totalPixels.toLocaleString()}`);
    console.log(`   差异像素:  ${result.mismatchCount.toLocaleString()}`);
    console.log(`   差异比例:  ${result.diffPercentage.toFixed(2)}%`);
    console.log(`   阈值:      ${(threshold * 100).toFixed(1)}%`);
    console.log(`   结果:      ${result.passed ? '✅ 通过' : '❌ 不通过'}`);
    console.log(`   差异图:    ${path.relative(PATHS.root, diffPath)}`);
  } else {
    basicCompare(figmaImage, screenshotPath);
  }
}

main().catch(console.error);
