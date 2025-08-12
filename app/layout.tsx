import type React from "react"
import type { Metadata } from "next"
import { Dancing_Script, Poppins } from "next/font/google"
import "./globals.css"

const dancingScript = Dancing_Script({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-dancing-script",
  weight: ["400", "600", "700"],
})

const poppins = Poppins({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-poppins",
  weight: ["300", "400", "500", "600"],
})

export const metadata: Metadata = {
  title: "tfbd Map",
  description: "Dance events and community map",
    generator: 'v0.dev'
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className={`${dancingScript.variable} ${poppins.variable}`}>
      <body className="antialiased">{children}</body>
    </html>
  )
}
