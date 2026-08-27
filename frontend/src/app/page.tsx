/**
 * Welcome page — placeholder shell.
 *
 * The real inbox UI lands in Phase 1 (see docs/ROADMAP.md). This exists so the app
 * boots and there is somewhere to hang the first components.
 */

export default function HomePage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-white px-6">
      <div className="w-full max-w-xl text-center">
        <p className="mb-3 font-medium text-gray-400 text-sm uppercase tracking-widest">
          ProjectEmail
        </p>

        <h1 className="mb-4 font-semibold text-4xl text-gray-900 tracking-tight sm:text-5xl">
          Welcome to ProjectEmail
        </h1>

        <p className="mb-10 text-gray-500 text-lg leading-relaxed">
          Disposable email, without the wait. Generate a temporary inbox, catch your
          verification code, and move on.
        </p>

        <div className="inline-flex items-center gap-2 rounded-full border border-gray-200 bg-gray-50 px-4 py-2">
          <span className="relative flex h-2 w-2">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-green-400 opacity-75" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-green-500" />
          </span>
          <span className="text-gray-600 text-sm">Frontend running — inbox UI coming in Phase 1</span>
        </div>

        <footer className="mt-16 border-gray-100 border-t pt-8">
          <p className="text-gray-400 text-sm">
            Read <code className="rounded bg-gray-100 px-1.5 py-0.5 text-gray-600">CLAUDE.md</code>{" "}
            before writing code.
          </p>
        </footer>
      </div>
    </main>
  );
}
