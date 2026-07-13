<?php
session_start();
if (!isset($_SESSION['user_id'])) { header("Location: index.php"); exit; }
$db = new PDO('sqlite:/tmp/app.db');
$db->exec("CREATE TABLE IF NOT EXISTS feedback (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, message TEXT, created_at DATETIME DEFAULT CURRENT_TIMESTAMP)");

$msg = '';
if ($_SERVER['REQUEST_METHOD'] === 'POST' && !empty($_POST['message'])) {
    $message = $_POST['message'];
    $username = $_SESSION['username'];
    $db->exec("INSERT INTO feedback (username, message) VALUES ('$username', '$message')");
    $msg = "Feedback posted.";
}

$flag = file_get_contents('/var/www/html/flag.txt');
$is_admin = ($_SESSION['username'] === 'admin');
?>
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Feedback Board</title><style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:system-ui,sans-serif;background:#f5f5f5;color:#1f1f1f;padding:40px 20px}
.card{background:#fff;border:1px solid #e0e0e0;border-radius:12px;padding:24px;margin:0 auto 16px;max-width:640px;box-shadow:0 1px 3px rgba(0,0,0,0.04)}
h1{font-size:1.5rem;margin-bottom:8px;color:#0067c0}h2{font-size:1rem;font-weight:600;margin-bottom:12px}
textarea{width:100%;padding:10px 12px;border:1px solid #d0d0d0;border-radius:8px;font-size:0.9rem;margin-bottom:10px;font-family:monospace;min-height:80px}
button{background:#0067c0;color:#fff;border:none;border-radius:8px;padding:10px 20px;font-weight:600;cursor:pointer}
button:hover{background:#005a9e}.success{color:#107c41;margin-bottom:12px}
.flag{font-family:monospace;font-size:1.1rem;color:#107c41;background:#ecfdf3;padding:12px;border-radius:8px;text-align:center;border:1px solid #86efac}
.comment{border-bottom:1px solid #eee;padding:10px 0;font-size:0.9rem}.comment strong{color:#0067c0}
.hint{font-size:0.8rem;color:#5c5c5c;margin-top:8px}a{color:#0067c0}
</style></head>
<body>
<div class="card">
<h1>Feedback Board</h1>
<p>Logged in as: <strong><?= htmlspecialchars($_SESSION['username']) ?></strong></p>
</div>

<?php if ($msg): ?>
<div class="card"><p class="success"><?= $msg ?></p></div>
<?php endif; ?>

<div class="card">
<h2>Post Feedback</h2>
<form method="POST">
<textarea name="message" placeholder="Write your feedback here..."></textarea>
<button type="submit">Submit</button>
</form>
<p class="hint">XSS: Try <strong>&lt;script&gt;alert('XSS')&lt;/script&gt;</strong> or <strong>&lt;img src=x onerror=alert(1)&gt;</strong></p>
<p class="hint">Goal: Steal the admin's cookie or make the admin view your payload to get the flag.</p>
</div>

<div class="card">
<h2>Recent Feedback</h2>
<?php $items = $db->query("SELECT * FROM feedback ORDER BY created_at DESC LIMIT 20");
if ($items) foreach ($items as $item): ?>
<div class="comment"><strong><?= htmlspecialchars($item['username']) ?>:</strong> <?= $item['message'] ?></div>
<?php endforeach; ?>
</div>

<?php if ($is_admin): ?>
<div class="card">
<h2>Flag</h2>
<p class="flag"><?= htmlspecialchars($flag) ?></p>
</div>
<?php endif; ?>

<div class="card">
<a href="index.php">Logout</a>
</div>
</body>
</html>
