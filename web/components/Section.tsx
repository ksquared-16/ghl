import { ReactNode } from "react";

interface SectionProps {
  children: ReactNode;
  className?: string;
  maxWidth?: "sm" | "md" | "lg" | "xl" | "2xl" | "full";
  id?: string;
}

export default function Section({
  children,
  className = "",
  maxWidth = "xl",
  id,
}: SectionProps) {
  const maxWidthClasses = {
    sm: "max-w-screen-sm",
    md: "max-w-screen-md",
    lg: "max-w-screen-lg",
    xl: "max-w-screen-xl",
    "2xl": "max-w-screen-2xl",
    full: "max-w-full",
  };

  return (
    <section
      id={id}
      className={`w-full px-4 sm:px-6 lg:px-8 mx-auto ${maxWidthClasses[maxWidth]} ${className}`}
    >
      {children}
    </section>
  );
}

