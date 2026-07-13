<?php
session_start();
if (!isset($_SESSION['user_id'])) { header("Location: login.php"); exit; }

$db = new PDO('sqlite:/tmp/app.db');
$profile_id = $_GET['id'] ?? $_SESSION['user_id'];

$stmt = $db->query("SELECT * FROM users WHERE id = $profile_id");
$profile = $stmt ? $stmt->fetch(PDO::FETCH_ASSOC) : null;
?>
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>User Profile</title><style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:system-ui,sans-serif;background:#f5f5f5;color:#1f1f1f;padding:40px 20px}
.card{background:#fff;border:1px solid #e0e0e0;border-radius:12px;padding:24px;margin:0 auto 16px;max-width:640px;box-shadow:0 1px 3px rgba(0,0,0,0.04)}
h1{font-size:1.5rem;margin-bottom:8px;color:#0067c0}
.field{margin-bottom:8px}.field label{font-weight:600;font-size:0.85rem;color:#5c5c5c;display:block}
.field .value{font-size:1rem}
pre{background:#111827;color:#e5e7eb;padding:16px;border-radius:8px;overflow-x:auto;font-size:0.85rem;margin-top:12px}
.hint{font-size:0.8rem;color:#5c5c5c;margin-top:8px}
a{color:#0067c0;text-decoration:none}a:hover{text-decoration:underline}
</style></head>
<body>
<div class="card">
<h1>Profile: <?= $profile ? htmlspecialchars($profile['username']) : 'Not Found' ?></h1>
<?php if ($profile): ?>
<div class="field"><label>ID</label><div class="value"><?= $profile['id'] ?></div></div>
<div class="field"><label>Username</label><div class="value"><?= htmlspecialchars($profile['username']) ?></div></div>
<div class="field"><label>Full Name</label><div class="value"><?= htmlspecialchars($profile['full_name']) ?></div></div>
<div class="field"><label>Email</label><div class="value"><?= htmlspecialchars($profile['email']) ?></div></div>
<div class="field"><label>Notes</label><pre><?= htmlspecialchars($profile['notes']) ?></pre></div>
<?php else: ?>
<p>User not found.</p>
<?php endif; ?>
</div>
<div class="card">
<a href="index.php">Back to Dashboard</a>
</div>
</body>
</html>
