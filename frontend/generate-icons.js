import { readFile, writeFile, mkdir } from 'fs/promises';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import sharp from 'sharp';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const sizes = [
  { size: 16, name: 'favicon-16x16.png' },
  { size: 32, name: 'favicon-32x32.png' },
  { size: 72, name: 'icon-72x72.png' },
  { size: 96, name: 'icon-96x96.png' },
  { size: 128, name: 'icon-128x128.png' },
  { size: 144, name: 'icon-144x144.png' },
  { size: 152, name: 'icon-152x152.png' },
  { size: 180, name: 'apple-touch-icon.png' },
  { size: 192, name: 'icon-192x192.png' },
  { size: 384, name: 'icon-384x384.png' },
  { size: 512, name: 'icon-512x512.png' },
];

const maskableSizes = [
  { size: 192, name: 'icon-maskable-192x192.png' },
  { size: 512, name: 'icon-maskable-512x512.png' },
];

const shortcutIcons = [
  { name: 'shortcut-overview.png', emoji: '📊' },
  { name: 'shortcut-portfolio.png', emoji: '💼' },
  { name: 'shortcut-analytics.png', emoji: '📈' },
  { name: 'shortcut-add.png', emoji: '➕' },
];

async function generateIcons() {
  const svgPath = join(__dirname, 'public', 'logo.svg');
  const iconsDir = join(__dirname, 'public', 'icons');

  // Create icons directory
  await mkdir(iconsDir, { recursive: true });

  const svgBuffer = await readFile(svgPath);

  console.log('🎨 Generating PWA icons...\n');

  // Generate standard icons
  for (const { size, name } of sizes) {
    const outputPath = join(iconsDir, name);
    await sharp(svgBuffer)
      .resize(size, size)
      .png()
      .toFile(outputPath);
    console.log(`✅ Generated: ${name}`);
  }

  // Generate maskable icons (with padding for safe zone)
  for (const { size, name } of maskableSizes) {
    const outputPath = join(iconsDir, name);
    const padding = Math.floor(size * 0.1); // 10% padding

    await sharp(svgBuffer)
      .resize(size - (padding * 2), size - (padding * 2))
      .extend({
        top: padding,
        bottom: padding,
        left: padding,
        right: padding,
        background: { r: 79, g: 70, b: 229, alpha: 1 } // theme color
      })
      .png()
      .toFile(outputPath);
    console.log(`✅ Generated maskable: ${name}`);
  }

  // Generate simple shortcut icons (simplified versions)
  for (const { name } of shortcutIcons) {
    const outputPath = join(iconsDir, name);
    await sharp(svgBuffer)
      .resize(96, 96)
      .png()
      .toFile(outputPath);
    console.log(`✅ Generated shortcut: ${name}`);
  }

  console.log('\n✨ All icons generated successfully!');
  console.log(`📁 Icons saved to: ${iconsDir}`);
}

generateIcons().catch(console.error);
