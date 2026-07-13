<?php
session_start();
if (!isset($_SESSION['user_id'])) { header("Location: login.php"); exit; }

$msg = '';
$error = '';

if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_FILES['avatar'])) {
    $target_dir = '/var/www/html/uploads/';
    $filename = basename($_FILES['avatar']['name']);
    $target_path = $target_dir . $filename;

    if (move_uploaded_file($_FILES['avatar']['tmp_name'], $target_path)) {
        $msg = "File uploaded: " . htmlspecialchars($filename);
    } else {
        $error = "Upload failed.";
    }
}

$uploaded_files = glob('/var/www/html/uploads/*');
?>
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Profile — Upload Lab</title><style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:system-ui,sans-serif;background:#f5f5f5;color:#1f1f1f;padding:40px 20px}
.card{background:#fff;border:1px solid #e0e0e0;border-radius:12px;padding:24px;margin:0 auto 16px;max-width:640px;box-shadow:0 1px 3px rgba(0,0,0,0.04)}
h1{font-size:1.5rem;margin-bottom:8px;color:#0067c0}h2{font-size:1rem;font-weight:600;margin-bottom:12px}
input[type=file]{margin-bottom:10px}.success{color:#107c41}.error{color:#c43e1c}
button{background:#0067c0;color:#fff;border:none;border-radius:8px;padding:10px 20px;font-weight:600;cursor:pointer}
button:hover{background:#005a9e}
pre{background:#111827;color:#e5e7eb;padding:16px;border-radius:8px;overflow-x:auto;font-size:0.85rem;margin-top:8px}
.hint{font-size:0.8rem;color:#5c5c5c;margin-top:8px}
a{color:#0067c0;display:inline-block;margin-right:8px;margin-top:4px}
</style></head>
<body>
<div class="card">
<h1>Profile Manager</h1>
<p>Logged in as: <strong><?= htmlspecialchars($_SESSION['username']) ?></strong></p>
</div>

<div class="card">
<h2>Upload Avatar</h2>
<?php if ($msg): ?><p class="success"><?= $msg ?></p><?php endif; ?>
<?php if ($error): ?><p class="error"><?= $error ?></p><?php endif; ?>
<form method="POST" enctype="multipart/form-data">
<input type="file" name="avatar" accept="image/*">
<button type="submit">Upload</button>
</form>
<p class="hint">No extension filtering — upload a <strong>.php</strong> webshell to get RCE.</p>
<p class="hint">Flag is at <strong>/var/www/html/flag.txt</strong> — read it from your webshell.</p>
</div>

<div class="card">
<h2>Uploaded Files</h2>
<?php if ($uploaded_files): foreach ($uploaded_files as $f): ?>
<a href="uploads/<?= basename($f) ?>"><?= basename($f) ?></a>
<?php endforeach; else: ?>
<p>No files uploaded yet.</p>
<?php endif; ?>
</div>

<div class="card">
<a href="login.php">Logout</a>
</div>
</body>
</html>
