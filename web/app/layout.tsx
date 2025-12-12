import type { Metadata } from "next";
import { Poppins } from "next/font/google";
import "./globals.css";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import GhlScript from "@/components/GhlScript";

const poppins = Poppins({
  weight: ["300", "400", "500", "600", "700"],
  subsets: ["latin"],
  variable: "--font-poppins",
});

export const metadata: Metadata = {
  title: "Alloy | Trusted Home Services in Bend",
  description: "Alloy connects homeowners with vetted local pros, starting with home cleaning in Bend, Oregon.",
  icons: {
    icon: "/brand/alloy-brandmark-blue.svg",
    apple: "/brand/alloy-brandmark-blue.svg",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${poppins.variable} font-sans antialiased`}>
        <GhlScript />
        <Navbar />
        <main>{children}</main>
        <Footer />
      </body>
    </html>
  );
}
