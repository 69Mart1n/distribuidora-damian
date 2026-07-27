import * as React from "react";
import { cn } from "@/lib/utils";

export function Card({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "rounded-2xl border border-stone-200/80 bg-white shadow-[0_1px_2px_rgba(28,25,23,.03),0_8px_30px_rgba(28,25,23,.04)]",
        className,
      )}
      {...props}
    />
  );
}
