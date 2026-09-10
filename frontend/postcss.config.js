/**
 * PostCSS Configuration
 * CSS processing configuration.
 *
 * Tailwind v4 ships its PostCSS plugin as a separate package and handles
 * vendor prefixing itself, so autoprefixer is no longer wired in here.
 *
 * Version: 2.0.0
 */

export default {
  plugins: {
    '@tailwindcss/postcss': {},
  },
}
