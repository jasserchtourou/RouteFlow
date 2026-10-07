import type { Metadata } from "next";
import { ComingSoon } from "@/components/ui/coming-soon";
import { PageHeader } from "@/components/ui/page-header";

export const metadata: Metadata = { title: "AI Assistant" };

export default function AIAssistantPage() {
  return (
    <>
      <PageHeader
        title="AI Assistant"
        description="Ask operational questions; answers cite tool results and documents."
      />
      <ComingSoon phase={18} what="Agentic RAG assistant" />
    </>
  );
}
