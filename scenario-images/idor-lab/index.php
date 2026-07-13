<?php
session_start();
if (!isset($_SESSION['user_id'])) { header("Location: login.php"); exit; }
?>
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Dashboard</title><style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:system-ui,sans-serif;background:#f5f5f5;color:#1f1f1f;padding:40px 20px}
.card{background:#fff;border:1px solid #e0e0e0;border-radius:12px;padding:24px;margin:0 auto 16px;max-width:640px;box-shadow:0 1px 3px rgba(0,0,0,0.04)}
h1{font-size:1.5rem;margin-bottom:8px;color:#0067c0}h2{font-size:1rem;font-weight:600;margin-bottom:12px}
.hint{font-size:0.8rem;color:#5c5c5c;margin-top:8px}
a{color:#0067c0;text-decoration:none;display:inline-block;margin-top:8px}a:hover{text-decoration:underline}
</style></head>
<body>
<div class="card">
<h1>Welcome, <?= htmlspecialchars($_SESSION['username']) ?></h1>
<p>Your user ID: <strong><?= $_SESSION['user_id'] ?></strong></p>
<a href="profile.php?id=<?= $_SESSION['user_id'] ?>">View My Profile</a>
</div>

<div class="card">
<h2>IDOR Challenge</h2>
<p>The flag is stored in admin's profile notes (user ID: 1).</p>
<p>Can you access it by changing the <strong>id</strong> parameter?</p>
<p class="hint">Try: <strong>profile.php?id=1</strong></p>
</div>

<div class="card">
<a href="login.php">Logout</a>
</div>
</body>
</html>
