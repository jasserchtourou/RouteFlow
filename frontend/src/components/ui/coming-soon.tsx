import { Construction } from "lucide-react";
import { Card } from "@/components/ui/card";

export function ComingSoon({ phase, what }: { phase: number; what: string }) {
  return (
    <Card className="flex flex-col items-center gap-3 py-16 text-center">
      <Construction aria-hidden className="size-8 text-accent" />
      <p className="font-medium">{what}</p>
      <p className="text-sm text-muted">Arrives in Phase {phase}.</p>
    </Card>
  );
}
