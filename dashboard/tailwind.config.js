/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
        serif: ['Fraunces', 'serif'],
      },
      colors: {
        // We will use zinc for our muted neutral palette and an indigo/blue for accent
        // But we can just use tailwind default zinc/blue.
      }
    },
  },
  plugins: [],
}
