<?php
session_start();
if (!isset($_SESSION['user_id'])) { header("Location: index.php"); exit; }
$db = new PDO('sqlite:/tmp/app.db');

$search = $_GET['q'] ?? '';
$results = [];
if ($search) {
    $stmt = $db->query("SELECT * FROM users WHERE username LIKE '%$search%' OR role LIKE '%$search%'");
    if ($stmt) $results = $stmt->fetchAll(PDO::FETCH_ASSOC);
}

$flag = file_get_contents('/var/www/html/flag.txt');
$is_admin = ($_SESSION['role'] === 'admin');
?>
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Dashboard</title><style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:system-ui,sans-serif;background:#f5f5f5;color:#1f1f1f;padding:40px 20px}
.card{background:#fff;border:1px solid #e0e0e0;border-radius:12px;padding:24px;margin:0 auto 16px;max-width:640px;box-shadow:0 1px 3px rgba(0,0,0,0.04)}
h1{font-size:1.5rem;margin-bottom:8px;color:#0067c0}h2{font-size:1rem;font-weight:600;margin-bottom:12px}
input{width:100%;padding:10px 12px;border:1px solid #d0d0d0;border-radius:8px;font-size:0.9rem;margin-bottom:10px}
button{background:#0067c0;color:#fff;border:none;border-radius:8px;padding:10px 20px;font-weight:600;cursor:pointer}
button:hover{background:#005a9e}.flag{font-family:monospace;font-size:1.1rem;color:#107c41;background:#ecfdf3;padding:12px;border-radius:8px;text-align:center;border:1px solid #86efac}
table{width:100%;border-collapse:collapse;font-size:0.85rem;margin-top:12px}
th,td{border:1px solid #e0e0e0;padding:8px 12px;text-align:left}
th{background:#f7f7f7}.hint{font-size:0.8rem;color:#5c5c5c;margin-top:8px}.nav{margin-top:16px;display:flex;gap:12px}
a{color:#0067c0;text-decoration:none}a:hover{text-decoration:underline}
</style></head>
<body>
<div class="card">
<h1>Welcome, <?= htmlspecialchars($_SESSION['username']) ?></h1>
<p>Role: <?= htmlspecialchars($_SESSION['role']) ?></p>
</div>

<div class="card">
<h2>Search Users</h2>
<form method="GET">
<input type="text" name="q" placeholder="Search by username or role..." value="<?= htmlspecialchars($search) ?>">
<button type="submit">Search</button>
</form>
<?php if ($results): ?>
<table><tr><th>ID</th><th>Username</th><th>Role</th></tr>
<?php foreach ($results as $r): ?>
<tr><td><?= $r['id'] ?></td><td><?= htmlspecialchars($r['username']) ?></td><td><?= $r['role'] ?></td></tr>
<?php endforeach; ?>
</table>
<?php elseif ($search): ?>
<p>No users found.</p>
<?php endif; ?>
<p class="hint">SQLi in search: <strong>' UNION SELECT id,username,password FROM users --</strong></p>
<p class="hint">Try UNION SELECT to read the flag file: <strong>' UNION SELECT 1,load_file('/var/www/html/flag.txt'),3 --</strong></p>
</div>

<?php if ($is_admin): ?>
<div class="card">
<h2>Flag</h2>
<p class="flag"><?= htmlspecialchars($flag) ?></p>
</div>
<?php endif; ?>

<div class="card">
<p class="hint">Not admin? Use SQL injection to log in as admin or extract the flag directly via UNION.</p>
<a href="index.php">Logout</a>
</div>
</body>
</html>
