#!/usr/bin/env node

/**
 * Figma 资源上传脚本
 * 将本地图片资源上传到 CDN 或对象存储
 *
 * 用法：
 *   node upload-figma-images.cjs --dir src/assets/images
 *   node upload-figma-images.cjs --dir src/assets/images --dry-run
 *
 * 环境变量：
 *   D2C_CDN_DOMAIN  — CDN 域名
 *   D2C_CDN_PREFIX  — CDN 路径前缀
 */

const fs = require('fs');
const path = require('path');
const { CDN, PATHS, IMAGE_CONFIG } = require('./config.cjs');

// ─── 参数解析 ────────────────────────────────
const args = process.argv.slice(2);

function getArg(name, defaultValue) {
  const idx = args.indexOf(`--${name}`);
  if (idx === -1) return defaultValue;
  if (typeof defaultValue === 'boolean') return true;
  return args[idx + 1] || defaultValue;
}

const targetDir = path.resolve(getArg('dir', PATHS.images));
const dryRun = getArg('dry-run', false);

// ─── 工具函数 ────────────────────────────────
function formatBytes(bytes) {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

function getFiles(dir, exts) {
  if (!fs.existsSync(dir)) {
    console.error(`❌ 目录不存在: ${dir}`);
    process.exit(1);
  }

  const files = [];
  const entries = fs.readdirSync(dir, { withFileTypes: true });

  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      files.push(...getFiles(fullPath, exts));
    } else if (entry.isFile()) {
      const ext = path.extname(entry.name).toLowerCase();
      if (exts.includes(ext)) {
        files.push(fullPath);
      }
    }
  }

  return files;
}

// ─── 上传模拟 ────────────────────────────────
// 实际项目中替换为真实的 CDN SDK 调用
async function uploadFile(localPath, remotePath) {
  // 模拟上传延迟
  await new Promise((resolve) => setTimeout(resolve, 100));

  return {
    success: true,
    url: `https://${CDN.imageDomain}${remotePath}`,
    size: fs.statSync(localPath).size,
  };
}

// ─── 生成 URL 映射表 ─────────────────────────
function generateUrlMapping(results) {
  const mapping = {};
  for (const result of results) {
    const importPath = result.localPath
      .replace(PATHS.root, '')
      .replace(/^\//, '');
    mapping[importPath] = result.cdnUrl;
  }
  return mapping;
}

// ─── 主流程 ──────────────────────────────────
async function main() {
  console.log('☁️  D2C 资源上传工具');
  console.log('━'.repeat(50));

  if (!CDN.enabled) {
    console.log('⚠️  CDN 未配置。请设置环境变量：');
    console.log('   export D2C_CDN_DOMAIN="cdn.example.com"');
    console.log('   export D2C_CDN_PREFIX="/assets/images/"');
    console.log('\n📋 以下文件待上传：\n');

    const files = getFiles(targetDir, IMAGE_CONFIG.supportedFormats);
    let totalSize = 0;

    for (const file of files) {
      const relativePath = path.relative(PATHS.root, file);
      const size = fs.statSync(file).size;
      totalSize += size;
      console.log(`  📄 ${relativePath} (${formatBytes(size)})`);
    }

    console.log(`\n📊 共 ${files.length} 个文件，总计 ${formatBytes(totalSize)}`);
    console.log('\n配置 CDN 后重新运行此脚本即可上传。');
    return;
  }

  console.log(`📂 源目录: ${targetDir}`);
  console.log(`🌐 CDN: https://${CDN.imageDomain}${CDN.imagePrefix}`);
  if (dryRun) console.log('⚡ 模拟运行模式');
  console.log('━'.repeat(50));

  const files = getFiles(targetDir, IMAGE_CONFIG.supportedFormats);

  if (files.length === 0) {
    console.log('📭 未找到可上传的文件');
    return;
  }

  console.log(`\n📋 准备上传 ${files.length} 个文件:\n`);

  const results = [];
  let successCount = 0;
  let failCount = 0;

  for (const file of files) {
    const relativePath = path.relative(PATHS.images, file);
    const remotePath = `${CDN.imagePrefix}${relativePath}`;
    const size = fs.statSync(file).size;

    if (dryRun) {
      console.log(`  ✅ [模拟] ${relativePath} → ${remotePath} (${formatBytes(size)})`);
      results.push({
        localPath: file,
        cdnUrl: `https://${CDN.imageDomain}${remotePath}`,
      });
      successCount++;
      continue;
    }

    try {
      const result = await uploadFile(file, remotePath);
      if (result.success) {
        console.log(`  ✅ ${relativePath} → ${result.url} (${formatBytes(size)})`);
        results.push({ localPath: file, cdnUrl: result.url });
        successCount++;
      }
    } catch (e) {
      console.log(`  ❌ ${relativePath} 上传失败: ${e.message}`);
      failCount++;
    }
  }

  // 生成 URL 映射表
  if (results.length > 0) {
    const mapping = generateUrlMapping(results);
    const mappingPath = path.join(PATHS.temp, 'cdn-url-mapping.json');

    if (!dryRun) {
      fs.mkdirSync(path.dirname(mappingPath), { recursive: true });
      fs.writeFileSync(mappingPath, JSON.stringify(mapping, null, 2), 'utf-8');
    }

    console.log(`\n📄 URL 映射表已生成: ${path.relative(PATHS.root, mappingPath)}`);
  }

  console.log('\n' + '━'.repeat(50));
  console.log('📊 上传结果:');
  console.log(`   成功: ${successCount}`);
  if (failCount > 0) console.log(`   失败: ${failCount}`);
  console.log('━'.repeat(50));
}

main().catch(console.error);
