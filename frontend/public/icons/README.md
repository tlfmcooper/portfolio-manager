# PWA Icons Generation Guide

This directory contains all the icons needed for the Progressive Web App (PWA) to work across different platforms and devices.

## Required Icon Sizes

### Standard Icons (any purpose)
- 72x72px
- 96x96px
- 128x128px
- 144x144px
- 152x152px
- 192x192px
- 384x384px
- 512x512px

### Maskable Icons (Android adaptive icons)
- 192x192px (maskable)
- 512x512px (maskable)

### Apple Touch Icons (iOS)
- 152x152px (iPad)
- 180x180px (iPhone)

### Favicons
- 16x16px
- 32x32px
- 48x48px

### Microsoft Tiles
- 144x144px (MS tile)

### Shortcuts Icons
- 96x96px (for each app shortcut)

## Icon Generation Options

### Option 1: Using PWA Asset Generator (Recommended)

```bash
# Install the generator
npm install -g @vite-pwa/assets-generator

# Generate icons from a single source image
# Place your source icon (at least 512x512px) as icon-source.svg or icon-source.png
npx @vite-pwa/assets-generator --preset minimal public/icon-source.svg
```

### Option 2: Using Online Tools

1. **RealFaviconGenerator** (https://realfavicongenerator.net/)
   - Upload your source icon
   - Select "Generate favicons for all platforms"
   - Download and extract to this directory

2. **PWA Builder** (https://www.pwabuilder.com/)
   - Enter your app URL
   - Generate icon package
   - Download and extract to this directory

3. **Favicon.io** (https://favicon.io/)
   - Upload your icon or create text-based icon
   - Download package
   - Extract to this directory

### Option 3: Manual Creation with Design Tools

Use tools like:
- Photoshop
- GIMP (free)
- Figma (free)
- Canva (free)

**Important**: For maskable icons, ensure the safe area is within the center 80% of the image.

## Maskable Icon Guidelines

Maskable icons need extra padding to prevent clipping on Android devices:

- Total size: 512x512px
- Safe zone: 410x410px (80%)
- Minimum safe zone: 256x256px (50%)
- Background: Should be a solid color or simple gradient
- Content: Keep all important elements within the safe zone

## Quick Start (Temporary Placeholders)

For development purposes, you can use placeholder icons:

```bash
# This will be generated automatically by vite-plugin-pwa
# Just ensure you have at least a basic icon in place
```

## Current Status

- [ ] 72x72 icon
- [ ] 96x96 icon
- [ ] 128x128 icon
- [ ] 144x144 icon
- [ ] 152x152 icon
- [ ] 192x192 icon
- [ ] 384x384 icon
- [ ] 512x512 icon
- [ ] 192x192 maskable icon
- [ ] 512x512 maskable icon
- [ ] Apple touch icons
- [ ] Favicons
- [ ] MS tile icons
- [ ] Shortcut icons

## Testing Icons

After generating icons, test them:

1. **Desktop Chrome**:
   - Open DevTools → Application → Manifest
   - Check that all icons are listed and load correctly

2. **Mobile Chrome (Android)**:
   - Install PWA to home screen
   - Check icon appearance on home screen
   - Check icon in app switcher

3. **Safari (iOS)**:
   - Add to home screen
   - Check icon appearance
   - Check splash screen

## Notes

- All icons should be PNG format
- Use lossless compression (TinyPNG, ImageOptim)
- Ensure consistent branding across all sizes
- Test on actual devices, not just emulators
