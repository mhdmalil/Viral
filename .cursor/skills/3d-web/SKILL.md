# Skill: 3D Web

## Purpose
Build genuinely justified, performant 3D/WebGL experiences when they meaningfully improve the
user experience — and firmly avoid 3D when it's just decoration.

## When This Skill Applies
Any request involving Three.js, WebGL, React Three Fiber, GLB/GLTF assets, or interactive
product visualization.

## Core Principle: Justify Before Building
Before writing any 3D code, answer explicitly:
- What does 3D accomplish here that a well-shot photo/video/CSS interaction couldn't?
- Is the performance and complexity cost worth that gain for this specific use case?

If the honest answer is "it would look cool," that is not sufficient justification. Say so and
propose the lighter-weight alternative instead.

## Good Candidate Use Cases
- Interactive product rotation / 360° viewing where photography can't substitute
- Material/color/configuration visualization (e.g., furniture, apparel, customizable products)
- A hero experience where spatial interaction is core to the product story
- Product customization tools that need real-time visual feedback

## Technical Practices
- Use compressed, optimized textures (appropriately sized, compressed formats) and optimized
  geometry (reasonable poly counts, draco/meshopt compression on GLTF where supported)
- Lazy-load the 3D bundle and assets — never block initial page render/LCP on 3D code
- Keep scene complexity limited: minimal unnecessary lights/shadows/post-processing
- Provide a graceful loading state and a static-image/CSS fallback for slow connections or
  unsupported devices
- Provide a mobile-appropriate experience — full desktop-grade 3D fidelity on a low-end mobile
  GPU often isn't appropriate; consider reduced fidelity or an image fallback
- Dispose of geometries/textures/renderers properly on unmount to avoid memory leaks
- Camera controls should be intuitive and constrained (don't let users navigate the camera into
  useless or disorienting positions)

## Checklist Before Shipping
- Confirmed justified per the core principle above
- Assets are compressed and reasonably sized
- Loads lazily, doesn't block critical rendering
- Has a fallback for low-end/unsupported cases
- Tested for smoothness on mobile, not just desktop
- Doesn't regress the page's overall performance budget (`performance` skill)

## Anti-Patterns to Avoid
- Adding a 3D hero purely because "it's impressive" with no product rationale
- Shipping uncompressed, unoptimized GLTF/texture assets
- Loading the 3D library/runtime eagerly on pages that don't need it
- No fallback for devices/browsers that can't run it well
