import { JarvisChat } from "@/components/chat/JarvisChat";

export default function JarvisPage() {
  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold">JARVIS</h1>
        <p className="text-muted-foreground mt-1">
          AI-Powered Paid Media Intelligence
        </p>
      </div>
      <JarvisChat />
    </div>
  );
}
