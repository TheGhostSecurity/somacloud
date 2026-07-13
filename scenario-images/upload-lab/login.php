<?php
session_start();
$db = new PDO('sqlite:/tmp/app.db');
$db->exec("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT, password TEXT)");
$db->exec("INSERT OR IGNORE INTO users VALUES (1,'admin','admin123')");
$db->exec("INSERT OR IGNORE INTO users VALUES (2,'user','user123')");

$error = '';
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $user = $_POST['username'] ?? '';
    $pass = $_POST['password'] ?? '';
    $sql = "SELECT * FROM users WHERE username='$user' AND password='$pass'";
    $result = $db->query($sql);
    if ($result && $row = $result->fetch(PDO::FETCH_ASSOC)) {
        $_SESSION['user_id'] = $row['id'];
        $_SESSION['username'] = $row['username'];
        header("Location: index.php");
        exit;
    }
    $error = "Invalid credentials.";
}
?>
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Upload Lab — Login</title><style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:system-ui,sans-serif;background:#f5f5f5;color:#1f1f1f;display:flex;justify-content:center;align-items:center;min-height:100vh}
.card{background:#fff;border:1px solid #e0e0e0;border-radius:12px;padding:32px;width:380px;box-shadow:0 1px 3px rgba(0,0,0,0.04)}
h1{font-size:1.5rem;margin-bottom:4px;color:#0067c0}.subtitle{color:#5c5c5c;margin-bottom:20px;font-size:0.9rem}
input{width:100%;padding:10px 12px;border:1px solid #d0d0d0;border-radius:8px;font-size:0.9rem;margin-bottom:12px}
button{width:100%;background:#0067c0;color:#fff;border:none;border-radius:8px;padding:10px;font-weight:600;cursor:pointer}
button:hover{background:#005a9e}.error{color:#c43e1c;margin-bottom:12px;font-size:0.9rem}
</style></head>
<body>
<div class="card">
<h1>Upload Lab</h1>
<p class="subtitle">Profile Manager</p>
<?php if ($error): ?><p class="error"><?= $error ?></p><?php endif; ?>
<form method="POST">
<input type="text" name="username" placeholder="Username">
<input type="password" name="password" placeholder="Password">
<button type="submit">Login</button>
</form>
<p style="margin-top:12px;font-size:0.8rem;color:#5c5c5c">Use: user / user123</p>
</div>
</body>
</html>
