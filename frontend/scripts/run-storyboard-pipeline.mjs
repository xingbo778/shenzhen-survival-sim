#!/usr/bin/env node
/**
 * Storyboard Platform Pipeline Test - Run 10 projects through full pipeline
 * Login → Create 10 projects → Generate Script → Anchor → Grid → Capture screenshots
 *
 * Run: cd others/shenzhen-pixel-city && npx node scripts/run-storyboard-pipeline.mjs
 */

import { chromium } from 'playwright';
import { mkdirSync, existsSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const BASE_URL = 'https://web-production-01d28.up.railway.app';
const START_INDEX = parseInt(process.env.START_INDEX || '0', 10);
const API_KEYS = process.env.STORYBOARD_API_KEY
  ? [process.env.STORYBOARD_API_KEY]
  : ['sb-batch-2026-railway'];
const SCREENSHOT_DIR = join(__dirname, '../../pipeline-test-screenshots');

// Project configs: L1, L2, L3 IDs from seed-categories.ts
const PROJECTS = [
  { title: '城市午夜飙车', l1: 'narrative', l2: 'narrative.chase', l3: 'narrative.chase.car', duration: '30' },
  { title: '咖啡馆的秘密', l1: 'narrative', l2: 'narrative.dialogue', l3: 'narrative.dialogue.cafe', duration: '30' },
  { title: '街头格斗高手', l1: 'narrative', l2: 'narrative.action', l3: 'narrative.action.martial', duration: '30' },
  { title: '废弃医院深夜', l1: 'narrative', l2: 'narrative.suspense', l3: 'narrative.suspense.horror', duration: '30' },
  { title: '初雪告白瞬间', l1: 'narrative', l2: 'narrative.romance', l3: 'narrative.romance.confession', duration: '30' },
  { title: '新款手机发布', l1: 'commercial', l2: 'commercial.product', l3: 'commercial.product.unboxing', duration: '15' },
  { title: '精品咖啡拉花', l1: 'commercial', l2: 'commercial.food', l3: 'commercial.food.recipe', duration: '15' },
  { title: '云南古镇漫步', l1: 'lifestyle', l2: 'lifestyle.travel', l3: 'lifestyle.travel.city', duration: '30' },
  { title: '霓虹雨夜独奏', l1: 'music_perf', l2: 'music_perf.mv', l3: 'music_perf.mv.narrative', duration: '30' },
  { title: '篮球队训练日', l1: 'special', l2: 'special.group', l3: 'special.group.ensemble', duration: '30' },
];

async function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

async function waitForSelector(page, selector, options = { timeout: 30000 }) {
  try {
    await page.waitForSelector(selector, options);
    return true;
  } catch {
    return false;
  }
}

async function login(context, page) {
  console.log('\n🔐 Attempting login...');
  await page.goto(BASE_URL, { waitUntil: 'domcontentloaded' });

  for (const key of API_KEYS) {
    console.log(`  Trying: ${key.substring(0, 8)}...`);
    await page.evaluate((k) => localStorage.setItem('storyboard-api-key', k), key);
    await page.reload({ waitUntil: 'networkidle' });
    await sleep(4000);
    const hasSidebar = await page.$('text=分类浏览');
    const hasLogin = await page.$('button:has-text("登录")');
    if (hasSidebar && !hasLogin) {
      console.log(`  ✅ Logged in`);
      return true;
    }
    // Form fallback for this key
    const input = await page.$('input[type="password"]');
    if (input) {
      await input.fill(key);
      await page.$('button:has-text("登录")').then((b) => b?.click());
      await sleep(6000);
      const hasNav = await page.$('text=分类浏览');
      if (hasNav) {
        console.log(`  ✅ Logged in via form`);
        return true;
      }
    }
  }
  console.log('  ❌ Login failed');
  return false;
}

async function createProject(page, config, index) {
  console.log(`\n📁 Creating project ${index + 1}: ${config.title}`);
  // Step-by-step: go to /browse, then L1, then L2, then L3 (simulates user navigation)
  await page.goto(`${BASE_URL}/browse`, { waitUntil: 'networkidle' });
  await sleep(2000);
  await page.goto(`${BASE_URL}/browse/${config.l1}`, { waitUntil: 'networkidle' });
  await sleep(1500);
  await page.goto(`${BASE_URL}/browse/${config.l1}/${config.l2}`, { waitUntil: 'networkidle' });
  await sleep(1500);
  await page.goto(`${BASE_URL}/browse/${config.l1}/${config.l2}/${config.l3}`, { waitUntil: 'networkidle' });
  await sleep(3000);

  const loginBtn = await page.$('button:has-text("登录")');
  if (loginBtn) {
    console.log('  ⚠️ Session lost');
    return null;
  }

  // Click 新建项目 - use getByRole for reliability
  const createBtn = page.getByRole('button', { name: /新建项目|新建/ });
  await createBtn.first().click({ timeout: 15000 });
  await sleep(2000);

  // Fill title
  await page.getByPlaceholder(/标题/).fill(config.title);
  await sleep(400);

  // Set duration - 4th Select in dialog
  try {
    const triggers = await page.locator('[role="dialog"] button[role="combobox"]').all();
    if (triggers.length >= 4) {
      await triggers[3].click({ timeout: 5000 });
      await sleep(600);
      await page.getByRole('option', { name: new RegExp(`${config.duration}秒`) }).click({ timeout: 3000 });
    }
  } catch (_) {}
  await sleep(300);

  // Click 创建
  await page.getByRole('button', { name: '创建' }).click({ timeout: 10000 });
  await sleep(5000);
  const url = page.url();
  if (url.includes('/project/')) {
    const id = url.match(/\/project\/(\d+)/)?.[1];
    console.log(`  ✅ Created project ID: ${id}`);
    return parseInt(id, 10);
  }
  console.log('  ❌ Failed to create project');
  return null;
}

async function clickAndConfirm(page, buttonSelector, confirmText = '确认重新生成') {
  const btn = await page.$(buttonSelector);
  if (!btn) return false;
  const disabled = await btn.getAttribute('disabled');
  if (disabled) return false;
  await btn.click();
  await sleep(500);
  const confirmBtn = await page.$(`button:has-text("${confirmText}")`);
  if (confirmBtn) {
    await confirmBtn.click();
    return true;
  }
  return true; // No confirm dialog
}

async function runPipeline(page, projectId, index) {
  console.log(`\n▶️ Running pipeline for project ${projectId} (${index + 1}/10)`);
  await page.goto(`${BASE_URL}/project/${projectId}`, { waitUntil: 'networkidle' });
  await sleep(3000);

  const results = { script: false, anchor: false, grid: false };

  // Step 1: 生成脚本 - click "生成脚本" or "执行" (Overview workflow step 1)
  const scriptBtn = await page.$('button:has-text("生成脚本"), button:has-text("执行")');
  if (scriptBtn) {
    await clickAndConfirm(page, 'button:has-text("生成脚本"), button:has-text("执行")');
    console.log('  ⏳ Generating script...');
    await sleep(3000);
    for (let i = 0; i < 90; i++) {
      await sleep(2000);
      const loading = await page.$('button:has-text("处理中"), [class*="animate-spin"]');
      const hasFrames = await page.$('text=帧, [class*="script"]');
      if (hasFrames || !loading) {
        results.script = true;
        console.log('  ✅ Script done');
        break;
      }
      if (i % 5 === 4) console.log(`    ... still generating (${(i + 1) * 2}s)`);
    }
  } else {
    const hasScript = await page.$('[class*="script"] [class*="Badge"], [data-slot="script"]');
    if (hasScript) results.script = true;
  }

  if (!results.script) {
    console.log('  ❌ Script generation failed or timed out');
    return results;
  }
  await sleep(2000);

  // Step 2: 生成Anchor
  const anchorBtn = await page.$('button:has-text("生成Anchor"), button:has-text("重新生成")');
  if (anchorBtn) {
    const disabled = await anchorBtn.getAttribute('disabled');
    if (!disabled) {
      await clickAndConfirm(page, 'button:has-text("生成Anchor"), button:has-text("重新生成")');
      console.log('  ⏳ Generating anchors...');
      await sleep(5000);
      for (let i = 0; i < 120; i++) {
        await sleep(2000);
        const loading = await page.$('button:has-text("Anchor生成中"), [class*="animate-spin"]');
        const anchorImgs = await page.$$('[class*="anchor"] img, img[src*="anchor"]');
        if (anchorImgs.length > 0 || !loading) {
          results.anchor = true;
          console.log('  ✅ Anchors done');
          break;
        }
        if (i % 5 === 4) console.log(`    ... still generating anchors (${(i + 1) * 2}s)`);
      }
    } else {
      const hasAnchors = await page.$$('[class*="anchor"] img');
      if (hasAnchors.length > 0) results.anchor = true;
    }
  }
  await sleep(2000);

  // Step 3: 生成Grid - switch to Grid tab first for direct button access
  const gridTab = await page.$('[role="tab"]:has-text("Grid"), [data-value="grid"]');
  if (gridTab) await gridTab.click();
  await sleep(1500);
  const gridBtn = await page.$('button:has-text("生成Grid")');
  if (gridBtn) {
    const disabled = await gridBtn.getAttribute('disabled');
    if (!disabled) {
      await clickAndConfirm(page, 'button:has-text("生成Grid")');
      console.log('  ⏳ Generating grid (2-5 min)...');
      await sleep(5000);
      for (let i = 0; i < 200; i++) {
        await sleep(2000);
        const gridGenerating = await page.$('text=Grid生成中');
        const gridImg = await page.$('img[src*="grid"], img[src*="panel"], img[alt*="分镜"]');
        if (gridImg && !gridGenerating) {
          results.grid = true;
          console.log('  ✅ Grid done');
          break;
        }
        if (i % 15 === 14) console.log(`    ... still generating grid (${Math.floor((i + 1) * 2 / 60)}min)`);
      }
    } else {
      const hasGrid = await page.$('img[src*="grid"], img[src*="panel"]');
      if (hasGrid) results.grid = true;
    }
  }
  return results;
}

async function captureGridScreenshot(page, projectId, title, index) {
  const gridImg = await page.$('img[alt*="Grid"], img[alt*="分镜"], [class*="grid"] img, img[src*="grid"]');
  if (gridImg) {
    const path = join(SCREENSHOT_DIR, `grid-${index + 1}-${projectId}-${title.replace(/[\\/:*?"<>|]/g, '_')}.png`);
    await gridImg.screenshot({ path });
    console.log(`  📸 Saved: ${path}`);
    return path;
  }
  // Fallback: full page
  const path = join(SCREENSHOT_DIR, `project-${index + 1}-${projectId}-full.png`);
  await page.screenshot({ path, fullPage: true });
  console.log(`  📸 Saved full page: ${path}`);
  return path;
}

async function main() {
  mkdirSync(SCREENSHOT_DIR, { recursive: true });
  console.log('🚀 Storyboard Pipeline Test');
  console.log(`   URL: ${BASE_URL}`);
  console.log(`   Screenshots: ${SCREENSHOT_DIR}`);
  if (START_INDEX > 0) console.log(`   Resuming from project ${START_INDEX + 1}/${PROJECTS.length}`);

  const browser = await chromium.launch({ headless: !!process.env.CI });
  const context = await browser.newContext({ viewport: { width: 1280, height: 800 } });
  const page = await context.newPage();

  const summary = { success: [], failed: [], screenshots: [] };

  try {
    const loggedIn = await login(context, page);
    if (!loggedIn) {
      console.log('\n❌ Cannot proceed without login');
      process.exit(1);
    }

    for (let i = START_INDEX; i < PROJECTS.length; i++) {
      const config = PROJECTS[i];
      const projectId = await createProject(page, config, i);
      if (!projectId) {
        summary.failed.push({ index: i + 1, title: config.title, reason: 'Create failed' });
        continue;
      }

      const results = await runPipeline(page, projectId, i);
      const path = await captureGridScreenshot(page, projectId, config.title, i);
      summary.screenshots.push({ projectId, title: config.title, path });

      if (results.grid) {
        summary.success.push({ index: i + 1, title: config.title, projectId });
      } else {
        summary.failed.push({
          index: i + 1,
          title: config.title,
          projectId,
          reason: `Script:${results.script} Anchor:${results.anchor} Grid:${results.grid}`,
        });
      }
    }
  } finally {
    await browser.close();
  }

  console.log('\n' + '='.repeat(60));
  console.log('📊 SUMMARY');
  console.log('='.repeat(60));
  console.log(`✅ Succeeded: ${summary.success.length}`);
  summary.success.forEach((s) => console.log(`   ${s.index}. ${s.title} (ID: ${s.projectId})`));
  console.log(`\n❌ Failed: ${summary.failed.length}`);
  summary.failed.forEach((f) => console.log(`   ${f.index}. ${f.title}: ${f.reason}`));
  console.log(`\n📸 Screenshots saved to: ${SCREENSHOT_DIR}`);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
