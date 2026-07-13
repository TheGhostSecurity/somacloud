<?php
$file = $_GET['file'] ?? 'info.php';
$content = '';
$base = '/var/www/html/';

$allowed = ['info.php', 'about.php', 'contact.php'];
if (in_array($file, $allowed)) {
    $content = file_get_contents($base . $file);
} elseif (strpos($file, '..') !== false || strpos($file, '/') !== false) {
    $path = $base . $file;
    if (file_exists($path)) {
        $content = file_get_contents($path);
    } else {
        $content = "File not found: " . htmlspecialchars($file);
    }
} else {
    $content = "Access denied or file not found.";
}
?>
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>LFI Lab</title><style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:system-ui,sans-serif;background:#f5f5f5;color:#1f1f1f;padding:40px 20px}
.card{background:#fff;border:1px solid #e0e0e0;border-radius:12px;padding:24px;margin:0 auto 16px;max-width:640px;box-shadow:0 1px 3px rgba(0,0,0,0.04)}
h1{font-size:1.5rem;margin-bottom:8px;color:#0067c0}h2{font-size:1rem;font-weight:600;margin-bottom:12px}
pre{background:#111827;color:#e5e7eb;padding:16px;border-radius:8px;overflow-x:auto;font-size:0.85rem;margin-top:12px;min-height:40px;white-space:pre-wrap;word-break:break-all}
.hint{font-size:0.8rem;color:#5c5c5c;margin-top:8px}
a{color:#0067c0;margin-right:12px;text-decoration:none}a:hover{text-decoration:underline}
</style></head>
<body>
<div class="card">
<h1>File Viewer</h1>
<p>Select a page to view:</p>
<a href="?file=info.php">Info</a>
<a href="?file=about.php">About</a>
<a href="?file=contact.php">Contact</a>
<hr style="margin:16px 0;border-color:#e0e0e0">
<p class="hint">LFI: <strong>?file=../../../var/www/html/flag.txt</strong></p>
<p class="hint">Log Poisoning: inject PHP code in User-Agent header, then include <strong>?file=../../../var/www/html/logs/access.log</strong></p>
</div>

<div class="card">
<h2>File Content: <?= htmlspecialchars(basename($file ?: 'info.php')) ?></h2>
<pre><?= htmlspecialchars($content) ?></pre>
</div>
</body>
</html>
