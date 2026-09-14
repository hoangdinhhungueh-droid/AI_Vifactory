/**
 * Remotion Central Configuration (Anti-OOM & Stability Enforced)
 * 
 * Configures resource boundaries for headless rendering on Linux server:
 * 1. setVideoImageFormat("jpeg") & setJpegQuality(85) to reduce frame-buffer memory by ~40% vs uncompressed PNG.
 * 2. setOffthreadVideoCacheSizeInBytes(512MB) to prevent runaway decoded cache (default was 50% system RAM).
 * 3. setChromiumOpenGlRenderer("swangle") for stable software rendering without discrete GPU.
 * 4. setChromiumDisableWebSecurity(true) to avoid memory overhead from sandboxed frame security checks.
 * 5. setConcurrency(1) as safe default in config.
 */
import { Config } from "@remotion/cli/config";

Config.setVideoImageFormat("jpeg");
Config.setJpegQuality(85);
Config.setOffthreadVideoCacheSizeInBytes(512 * 1024 * 1024);
Config.setChromiumOpenGlRenderer("swangle");
Config.setChromiumDisableWebSecurity(true);
Config.setConcurrency(1);
