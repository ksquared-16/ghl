import { ReactNode } from "react";

interface BrandValueCardProps {
  title: string;
  description: string;
  icon?: ReactNode;
  accentColor?: "juniper" | "ember" | "blue" | "pine";
}

export default function BrandValueCard({
  title,
  description,
  icon,
  accentColor = "juniper",
}: BrandValueCardProps) {
  const accentColors = {
    juniper: "text-alloy-juniper",
    ember: "text-alloy-ember",
    blue: "text-alloy-blue",
    pine: "text-alloy-pine",
  };

  return (
    <div className="bg-white rounded-2xl p-8 border border-alloy-stone/50 shadow-sm hover:shadow-md transition-shadow">
      {icon && (
        <div className={`mb-4 ${accentColors[accentColor]}`}>{icon}</div>
      )}
      <h3 className="text-xl font-semibold text-alloy-pine mb-3">{title}</h3>
      <p className="text-alloy-midnight/80">{description}</p>
    </div>
  );
}

