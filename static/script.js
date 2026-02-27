'use strict';

// element toggle function
const elementToggleFunc = function (elem) { elem.classList.toggle("active"); }

// ================= SIDEBAR =================
const sidebar = document.querySelector("[data-sidebar]");
const sidebarBtn = document.querySelector("[data-sidebar-btn]");

if (sidebarBtn && sidebar) {
  sidebarBtn.addEventListener("click", function () {
    elementToggleFunc(sidebar);
  });
}

// ================= CONTACT FORM =================
const form = document.querySelector("[data-form]");
const formInputs = document.querySelectorAll("[data-form-input]");
const formBtn = document.querySelector("[data-form-btn]");

if (form) {

  formInputs.forEach(input => {
    input.addEventListener("input", function () {
      if (form.checkValidity()) {
        formBtn.removeAttribute("disabled");
      } else {
        formBtn.setAttribute("disabled", "");
      }
    });
  });

  form.addEventListener("submit", async function (e) {
    e.preventDefault();

    const formData = new FormData(form);
    const data = {
      fullname: formData.get("fullname"),
      email: formData.get("email"),
      message: formData.get("message")
    };

    try {
      const response = await fetch("/api/contact", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data)
      });

      const result = await response.json();

      if (result.status === "success") {
        alert("Message sent successfully!");
        form.reset();
        formBtn.setAttribute("disabled", "");
      } else {
        alert("Error: " + result.message);
      }

    } catch (error) {
      alert("Failed to send message.");
      console.error(error);
    }
  });
}

// ================= AUTH FORMS =================
const authForms = document.querySelectorAll("[data-auth-form]");
const passwordToggleButtons = document.querySelectorAll("[data-toggle-password]");

function validateAuthForm(authForm) {
  const username = authForm.querySelector('[name="username"], [name="new_username"]');
  const currentPassword = authForm.querySelector('[name="password"], [name="current_password"]');
  const newPassword = authForm.querySelector('[name="new_password"]');
  const confirmPassword = authForm.querySelector('[name="confirm_password"]');
  const submitBtn = authForm.querySelector("[data-submit-btn]");
  let valid = true;

  const setError = (fieldName, message) => {
    const errorEl = authForm.querySelector(`[data-error-for="${fieldName}"]`);
    if (errorEl) errorEl.textContent = message || "";
  };

  if (username) {
    const usernameValue = username.value.trim();
    if (usernameValue.length < 3) {
      valid = false;
      setError(username.name, "Username must be at least 3 characters.");
    } else {
      setError(username.name, "");
    }
  }

  if (currentPassword) {
    const passwordValue = currentPassword.value;
    if (!passwordValue) {
      valid = false;
      setError(currentPassword.name, "Password is required.");
    } else {
      setError(currentPassword.name, "");
    }
  }

  if (newPassword && confirmPassword) {
    const newPasswordValue = newPassword.value;
    const confirmValue = confirmPassword.value;

    if (newPasswordValue && newPasswordValue.length < 6) {
      valid = false;
      setError("new_password", "New password must be at least 6 characters.");
    } else {
      setError("new_password", "");
    }

    if (newPasswordValue !== confirmValue) {
      if (confirmValue || newPasswordValue) {
        valid = false;
        setError("confirm_password", "Passwords do not match.");
      }
    } else {
      setError("confirm_password", "");
    }

    const strengthEl = authForm.querySelector("[data-password-strength]");
    if (strengthEl) {
      if (!newPasswordValue) {
        strengthEl.textContent = "";
      } else if (newPasswordValue.length < 8) {
        strengthEl.textContent = "Password strength: Weak";
      } else if (/[A-Z]/.test(newPasswordValue) && /\d/.test(newPasswordValue) && /[^A-Za-z0-9]/.test(newPasswordValue)) {
        strengthEl.textContent = "Password strength: Strong";
      } else {
        strengthEl.textContent = "Password strength: Medium";
      }
    }
  }

  if (submitBtn) submitBtn.disabled = !valid;
  return valid;
}

if (authForms.length > 0) {
  authForms.forEach((authForm) => {
    const fields = authForm.querySelectorAll("input");
    fields.forEach((field) => {
      field.addEventListener("input", () => validateAuthForm(authForm));
    });

    authForm.addEventListener("submit", (event) => {
      if (!validateAuthForm(authForm)) {
        event.preventDefault();
        return;
      }
      const submitBtn = authForm.querySelector("[data-submit-btn]");
      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.classList.add("is-loading");
        submitBtn.innerHTML = "<span>Please wait...</span>";
      }
    });

    validateAuthForm(authForm);
  });
}

if (passwordToggleButtons.length > 0) {
  passwordToggleButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      const targetId = btn.getAttribute("data-target");
      if (!targetId) return;
      const targetInput = document.getElementById(targetId);
      if (!targetInput) return;
      const isHidden = targetInput.type === "password";
      targetInput.type = isHidden ? "text" : "password";
      btn.textContent = isHidden ? "Hide" : "Show";
      btn.setAttribute("aria-label", isHidden ? "Hide password" : "Show password");
    });
  });
}

// ================= BLOG =================
const blogForm = document.querySelector("[data-blog-form]");
const blogBtn = document.querySelector("[data-blog-btn]");
const blogsContainer = document.getElementById("blogs-container");
const isAdmin = document.body?.dataset?.isAdmin === "true";
const blogModal = document.getElementById("blogModal");
const blogModalTitle = document.getElementById("blogModalTitle");
const blogModalMeta = document.getElementById("blogModalMeta");
const blogModalContent = document.getElementById("blogModalContent");
const blogModalCloseBtn = document.getElementById("blogModalCloseBtn");

async function loadBlogs() {
  try {
    const response = await fetch("/api/blogs");
    const blogs = await response.json();
    displayBlogs(blogs);
  } catch (error) {
    console.error("Error loading blogs:", error);
  }
}

function displayBlogs(blogs) {
  if (!blogsContainer) return;

  blogsContainer.style.display = "flex";
  blogsContainer.style.flexDirection = "column";
  blogsContainer.style.gap = "16px";
  blogsContainer.innerHTML = "";

  if (blogs.length === 0) {
    blogsContainer.innerHTML =
      "<p style='text-align:center;color:#999;'>No blogs yet.</p>";
    return;
  }

  blogs.forEach((blog, index) => {
    const date = formatDate(blog.timestamp);
    const rawTitle = String(blog.title || "");
    const rawCategory = String(blog.category || "");
    const rawContent = String(blog.content || "");
    const previewRaw = rawContent.length > 220 ? `${rawContent.slice(0, 220)}...` : rawContent;
    const previewContent = escapeHtml(previewRaw).replace(/\n/g, "<br>");
    const safeTitle = JSON.stringify(rawTitle);
    const safeCategory = JSON.stringify(rawCategory);
    const safeDate = JSON.stringify(date);
    const safeContent = JSON.stringify(rawContent);
    let adminActions = "";

    const escapedTitle = escapeHtml(rawTitle);
    if (isAdmin) {
      adminActions = `
          <div class="blog-admin-actions">
            <button class="form-btn"
              aria-label="Edit blog ${escapedTitle}"
              onclick='editBlog(${blog.id}, ${safeTitle}, ${safeCategory}, ${safeContent})'>
              Edit
            </button>
            <button class="form-btn"
              aria-label="Delete blog ${escapedTitle}"
              style="background-color:#ff6b6b;"
              onclick="deleteBlog(${blog.id})">
              Delete
            </button>
          </div>
      `;
    }

    blogsContainer.innerHTML += `
      <li class="blog-post-item">
        <div class="blog-content blog-sequence-card">
          <span class="blog-seq-badge">#${index + 1}</span>
          <div class="blog-meta">
            <p class="blog-category">${blog.category}</p>
            <span class="dot"></span>
            <time>${date}</time>
          </div>
          <h3 class="h3 blog-item-title">
            <button class="blog-open-btn" onclick='openBlogModal(${blog.id}, ${safeTitle}, ${safeCategory}, ${safeDate}, ${safeContent})' aria-label="Open full blog ${escapedTitle}">
              ${escapedTitle}
            </button>
          </h3>
          <p class="blog-text">${previewContent}</p>
          <button class="blog-read-btn" onclick='openBlogModal(${blog.id}, ${safeTitle}, ${safeCategory}, ${safeDate}, ${safeContent})' aria-label="Read full blog ${escapedTitle}">
            Read Full
          </button>
          ${adminActions}
        </div>
      </li>
    `;
  });
}

window.openBlogModal = function (_blogId, title, category, date, content) {
  if (!blogModal || !blogModalTitle || !blogModalMeta || !blogModalContent) return;
  blogModalTitle.textContent = title;
  blogModalMeta.textContent = `${category} • ${date}`;
  blogModalContent.innerHTML = escapeHtml(content).replace(/\n/g, "<br>");
  blogModal.classList.add("active");
  blogModal.setAttribute("aria-hidden", "false");
};

window.closeBlogModal = function () {
  if (!blogModal) return;
  blogModal.classList.remove("active");
  blogModal.setAttribute("aria-hidden", "true");
};

function editBlog(id, title, category, content) {
  if (!isAdmin || !blogForm || !blogBtn) return;
  document.querySelector('[name="title"]').value = title;
  document.querySelector('[name="category"]').value = category;
  document.querySelector('[name="content"]').value = content;
  blogForm.dataset.blogId = id;
  blogBtn.innerHTML = "Update Blog";
  window.scrollTo(0, 0);
}

async function deleteBlog(id) {
  if (!isAdmin) return;
  if (!confirm("Delete this blog?")) return;

  try {
    const response = await fetch(`/api/blogs/${id}`, { method: "DELETE" });
    if (response.ok) {
      loadBlogs();
    }
  } catch (error) {
    console.error(error);
  }
}

if (blogsContainer) {
  loadBlogs();
}

if (blogModalCloseBtn) {
  blogModalCloseBtn.addEventListener("click", window.closeBlogModal);
}
if (blogModal) {
  blogModal.addEventListener("click", (event) => {
    if (event.target === blogModal) {
      window.closeBlogModal();
    }
  });
}
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    window.closeBlogModal();
  }
});

if (blogForm && isAdmin) {
  blogForm.addEventListener("submit", async function (e) {
    e.preventDefault();

    const formData = new FormData(blogForm);
    const data = {
      title: formData.get("title"),
      category: formData.get("category"),
      content: formData.get("content")
    };

    const blogId = blogForm.dataset.blogId;
    const url = blogId ? `/api/blogs/${blogId}` : "/api/blogs";
    const method = blogId ? "PUT" : "POST";

    const response = await fetch(url, {
      method: method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data)
    });

    if (response.ok) {
      blogForm.reset();
      delete blogForm.dataset.blogId;
      blogBtn.innerHTML = "Publish Blog";
      loadBlogs();
    }
  });
}

// ================= DAILY ROUTINE =================

const postForm = document.getElementById("postForm");
const postsContainer = document.getElementById("postsContainer");

function parseTimestamp(value) {
  const raw = String(value || "");
  if (!raw) return new Date();

  // If timezone info is present, let Date parse it.
  if (/[zZ]|[+-]\d{2}:\d{2}$/.test(raw)) {
    return new Date(raw);
  }

  // Parse as local time when timezone is missing.
  const match = raw.match(
    /^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2}):(\d{2})/
  );
  if (match) {
    const [, y, m, d, hh, mm, ss] = match.map(Number);
    return new Date(y, m - 1, d, hh, mm, ss);
  }

  return new Date(raw);
}

const APP_TIMEZONE = document.body?.dataset?.timezone || "Asia/Kolkata";

function formatDate(value) {
  const date = parseTimestamp(value);
  return date.toLocaleDateString("en-IN", {
    timeZone: APP_TIMEZONE,
    year: "numeric",
    month: "short",
    day: "2-digit"
  });
}

function formatTime(value) {
  const date = parseTimestamp(value);
  return date.toLocaleString("en-IN", {
    timeZone: APP_TIMEZONE,
    year: "numeric",
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit"
  });
}

function escapeHtml(text) {
  const map = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#039;'
  };
  return text.replace(/[&<>"']/g, m => map[m]);
}

if (postsContainer) {

  let routinePosts = [];

  async function loadPosts() {
    try {
      const response = await fetch('/api/routine/posts');
      routinePosts = await response.json();
      renderPosts();
    } catch (error) {
      console.error('Error loading posts:', error);
    }
  }

  function renderPosts() {
    postsContainer.innerHTML = "";

    if (routinePosts.length === 0) {
      postsContainer.innerHTML =
        '<div class="empty-state"><p>No posts yet.</p></div>';
      return;
    }

    routinePosts.forEach(post => {
      let html = `
        <div class="post-card">
          <div class="post-header">
            <div class="post-time">${formatTime(post.timestamp)}</div>
          </div>
          <div class="post-message">${escapeHtml(post.message)}</div>
      `;

      if (isAdmin) {
        html += `
          <div class="post-actions">
            <button class="btn-reply"
              onclick="toggleReplyForm(${post.id})">
              Reply
            </button>
          </div>

          <div class="reply-form" id="replyForm-${post.id}">
            <textarea id="replyText-${post.id}" rows="3"
              placeholder="Write a reply..."></textarea>
            <button onclick="submitReply(${post.id})">
              Post Reply
            </button>
          </div>
        `;
      }

      if (post.replies && post.replies.length > 0) {
        html += `<div class="replies-container">`;

        post.replies.forEach(reply => {
          html += `
            <div class="reply-item">
              <div class="reply-time">
                ${formatTime(reply.timestamp)}
              </div>
              <div class="reply-text">
                ${escapeHtml(reply.message)}
              </div>
            </div>
          `;
        });

        html += `</div>`;
      }

      html += `</div>`;

      postsContainer.innerHTML += html;
    });
  }

  window.toggleReplyForm = function (postId) {
    const form = document.getElementById(`replyForm-${postId}`);
    if (form) form.classList.toggle("show");
  };

  window.submitReply = async function (postId) {
    if (!isAdmin) return;
    const input = document.getElementById(`replyText-${postId}`);
    if (!input) return;
    const message = input.value.trim();
    if (!message) return;

    try {
      const response = await fetch(
        `/api/routine/reply/${postId}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message })
        }
      );

      if (response.ok) {
        input.value = "";
        loadPosts();
      }
    } catch (error) {
      console.error("Error replying:", error);
    }
  };

  if (postForm && isAdmin) {
    postForm.addEventListener("submit", async (e) => {
      e.preventDefault();

      const message =
        document.getElementById("postMessage").value.trim();
      if (!message) return;

      await fetch("/api/routine/post", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message })
      });

      document.getElementById("postMessage").value = "";
      loadPosts();
    });
  }

  loadPosts();
}
