/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        neoBg: '#f4f4f5',
        neoCard: '#ffffff',
        neoBorder: '#000000',
        neoMain: '#000000',
        neoMainHover: '#27272a',
        neoMuted: '#71717a',
        neoGray: '#e4e4e7',
        neoDark: '#18181b',
        neoLight: '#fafafa',
      },
      borderRadius: {
        base: '6px',
      },
      boxShadow: {
        neo: '4px 4px 0px 0px #000000',
        'neo-sm': '2px 2px 0px 0px #000000',
        'neo-md': '3px 3px 0px 0px #000000',
        'neo-lg': '6px 6px 0px 0px #000000',
        'neo-xl': '8px 8px 0px 0px #000000',
        'neo-active': '0px 0px 0px 0px #000000',
      },
      borderWidth: {
        'neo': '2px',
        'neo-thick': '3px',
      }
    },
  },
  plugins: [],
}
