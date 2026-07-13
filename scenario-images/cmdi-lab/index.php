<?php
$output = '';
$target = $_POST['target'] ?? '';
if ($target) {
    $output = shell_exec("ping -c 2 $target 2>&1");
}

$flag_path = '/var/www/html/flag.txt';
$flag_found = false;
if (file_exists($flag_path)) {
    $flag_found = true;
}
?>
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>CMDi Lab</title><style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:system-ui,sans-serif;background:#f5f5f5;color:#1f1f1f;padding:40px 20px}
.card{background:#fff;border:1px solid #e0e0e0;border-radius:12px;padding:24px;margin:0 auto 16px;max-width:640px;box-shadow:0 1px 3px rgba(0,0,0,0.04)}
h1{font-size:1.5rem;margin-bottom:8px;color:#0067c0}h2{font-size:1rem;font-weight:600;margin-bottom:12px}
input{width:100%;padding:10px 12px;border:1px solid #d0d0d0;border-radius:8px;font-size:0.9rem;margin-bottom:10px}
button{background:#0067c0;color:#fff;border:none;border-radius:8px;padding:10px 20px;font-weight:600;cursor:pointer}
button:hover{background:#005a9e}
pre{background:#111827;color:#e5e7eb;padding:16px;border-radius:8px;overflow-x:auto;font-size:0.85rem;margin-top:12px;min-height:40px;white-space:pre-wrap;word-break:break-all}
.hint{font-size:0.8rem;color:#5c5c5c;margin-top:8px}
</style></head>
<body>
<div class="card">
<h1>Network Ping Tool</h1>
<p class="hint">Enter an IP address or hostname to ping.</p>
<form method="POST">
<input type="text" name="target" placeholder="e.g. 127.0.0.1" value="<?= htmlspecialchars($target) ?>">
<button type="submit">Ping</button>
</form>
<?php if ($output): ?>
<h2>Output</h2>
<pre><?= htmlspecialchars($output) ?></pre>
<?php endif; ?>
<p class="hint">Command Injection: <strong>127.0.0.1; cat /var/www/html/flag.txt</strong></p>
<p class="hint">Try: <strong>$(cat /var/www/html/flag.txt)</strong> or backticks.</p>
</div>
</body>
</html>
