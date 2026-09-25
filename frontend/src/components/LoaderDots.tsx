export function LoaderDots({ className = "" }: { className?: string }) {
  return (
    <span className={className ? `loader-dots ${className}` : "loader-dots"} aria-hidden="true">
      <span className="loader-dot" />
      <span className="loader-dot" />
      <span className="loader-dot" />
    </span>
  );
}
