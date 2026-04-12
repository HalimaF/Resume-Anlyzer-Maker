// Cover Letter Generator Logic

let currentTemplate = 'classic';

// Initialize theme on page load
document.addEventListener('DOMContentLoaded', () => {
  const savedTheme = localStorage.getItem('theme') || 'light';
  document.documentElement.setAttribute('data-theme', savedTheme);
  updateThemeButton();
});

// Theme Toggle
function toggleTheme() {
  const html = document.documentElement;
  const currentTheme = html.getAttribute('data-theme') || 'light';
  const newTheme = currentTheme === 'light' ? 'dark' : 'light';
  
  html.setAttribute('data-theme', newTheme);
  localStorage.setItem('theme', newTheme);
  updateThemeButton();
}

function updateThemeButton() {
  const button = document.querySelector('.theme-toggle');
  const theme = document.documentElement.getAttribute('data-theme') || 'light';
  if (theme === 'dark') {
    button.innerHTML = '<i class="fa-solid fa-sun"></i>';
  } else {
    button.innerHTML = '<i class="fa-solid fa-moon"></i>';
  }
}

// Template Selection
function selectTemplate(template) {
  currentTemplate = template;
  document.querySelectorAll('.template-card').forEach(card => {
    card.classList.remove('active');
  });
  event.target.closest('.template-card').classList.add('active');
  
  // Re-generate with new template if content exists
  if (document.getElementById('fullName').value) {
    generateCoverLetter();
  }
}

// Generate Cover Letter
function generateCoverLetter() {
  const fullName = document.getElementById('fullName').value.trim();
  const email = document.getElementById('email').value.trim();
  const phone = document.getElementById('phone').value.trim();
  const linkedIn = document.getElementById('linkedIn').value.trim();
  const website = document.getElementById('website').value.trim();
  const hireManagerName = document.getElementById('hireManagerName').value.trim();
  const companyName = document.getElementById('companyName').value.trim();
  const jobTitle = document.getElementById('jobTitle').value.trim();
  const jobDescription = document.getElementById('jobDescription').value.trim();
  const resumeHighlights = document.getElementById('resumeHighlights').value.trim();
  const personalityTone = document.getElementById('personalityTone').value;
  const whyCompany = document.getElementById('whyCompany').value.trim();

  // Validation
  if (!fullName || !email || !companyName || !jobTitle) {
    alert('Please fill in Name, Email, Company, and Job Title (required fields)');
    return;
  }

  // Generate letter content
  const letterContent = generateLetterContent({
    fullName,
    email,
    phone,
    linkedIn,
    website,
    hireManagerName,
    companyName,
    jobTitle,
    jobDescription,
    resumeHighlights,
    personalityTone,
    whyCompany
  });

  // Display in preview
  const preview = document.getElementById('coverLetterPreview');
  preview.innerHTML = letterContent;

  // Show success feedback
  showNotification('Cover letter generated successfully!', 'success');
}

// Generate Letter Content Based on Template and Tone
function generateLetterContent(data) {
  const {
    fullName,
    email,
    phone,
    linkedIn,
    website,
    hireManagerName,
    companyName,
    jobTitle,
    jobDescription,
    resumeHighlights,
    personalityTone,
    whyCompany
  } = data;

  const today = new Date();
  const dateStr = today.toLocaleDateString('en-US', { 
    year: 'numeric', 
    month: 'long', 
    day: 'numeric' 
  });

  // Generate opening paragraph based on tone and job description
  let openingPara = generateOpeningParagraph(
    jobTitle,
    companyName,
    hireManagerName,
    personalityTone,
    jobDescription
  );

  // Generate body paragraph highlighting achievements
  let bodyPara = generateBodyParagraph(
    resumeHighlights,
    jobDescription,
    personalityTone,
    jobTitle
  );

  // Generate closing paragraph
  let closingPara = generateClosingParagraph(
    whyCompany,
    companyName,
    personalityTone
  );

  // Build contact info display
  let contactInfo = `<p>${fullName}</p>`;
  if (email) contactInfo += `<p>${email}</p>`;
  if (phone) contactInfo += `<p>${phone}</p>`;
  if (linkedIn) contactInfo += `<p><a href="${linkedIn}" style="color: #3498db; text-decoration: none;">LinkedIn</a></p>`;
  if (website) contactInfo += `<p><a href="${website}" style="color: #3498db; text-decoration: none;">Portfolio</a></p>`;

  // Build recipient info
  let recipientInfo = `<p>${hireManagerName ? `Dear ${hireManagerName},` : 'Dear Hiring Manager,'}</p>`;

  // Select template style
  let headerStyle = '';
  if (currentTemplate === 'modern') {
    headerStyle = 'border-left: 4px solid #3498db; padding-left: 1rem;';
  } else if (currentTemplate === 'minimal') {
    headerStyle = 'text-align: center; border-bottom: 1px solid #ccc; padding-bottom: 1rem;';
  }

  return `
    <div class="cover-letter-content">
      <div class="letter-header" style="${headerStyle}">
        <div class="sender-info">
          <strong style="${currentTemplate === 'minimal' ? 'font-size: 1.2rem;' : ''}">${fullName}</strong>
          ${contactInfo}
        </div>
        <div class="date">${dateStr}</div>
      </div>

      <div class="recipient-info">
        ${recipientInfo}
      </div>

      <div class="greeting">
        ${hireManagerName ? `I am writing to express my strong interest in the ${jobTitle} position at ${companyName}.` : `I am excited to apply for the ${jobTitle} position at ${companyName}.`}
      </div>

      <div class="letter-body">
        ${openingPara}
        ${bodyPara}
        ${closingPara}
      </div>

      <div class="letter-closing">
        <div class="closing-statement">
          ${getClosingStatement(personalityTone)}
        </div>
        <div class="signature-line">
          <div class="signature-name">${fullName}</div>
        </div>
      </div>
    </div>
  `;
}

// Generate opening paragraph
function generateOpeningParagraph(jobTitle, companyName, hireManagerName, tone, jobDescription) {
  const openings = {
    professional: [
      `With my extensive background in ${jobTitle === 'Senior' ? 'senior-level' : ''} roles and proven track record of delivering results, I am confident in my ability to contribute meaningfully to ${companyName}'s success.`,
      `I am writing to apply for the ${jobTitle} position at ${companyName}. Your organization's commitment to excellence align perfectly with my professional values and career aspirations.`,
      `Your job posting resonates strongly with my professional background and expertise. I am enthusiastic about the opportunity to bring my skills and experience to ${companyName}'s team.`
    ],
    friendly: [
      `I was thrilled to see the ${jobTitle} opening at ${companyName}! Your company's mission and values have always impressed me, and I'd love to be part of your team.`,
      `I'm excited to apply for the ${jobTitle} position at ${companyName}. I've followed your company's growth and innovations, and I'm genuinely enthusiastic about contributing to your success.`,
      `When I came across the ${jobTitle} opportunity at ${companyName}, I immediately knew this was the perfect match for my skills and passion for growth.`
    ],
    creative: [
      `The ${jobTitle} position at ${companyName} represents an exciting opportunity to merge my innovative mindset with your organization's dynamic vision for the future.`,
      `I am drawn to ${companyName}'s bold approach to ${jobDescription ? 'solving industry challenges' : 'innovation'}. As a creative problem-solver, I'm eager to contribute fresh perspectives to your team.`,
      `Your vision for ${companyName} excites me. With my background and passion for innovation, I'm confident I can help drive meaningful progress in this ${jobTitle} role.`
    ],
    technical: [
      `I am applying for the ${jobTitle} role at ${companyName}, where I can leverage my technical expertise and proficiency in ${jobDescription ? 'your required technologies' : 'modern development practices'} to drive impactful solutions.`,
      `Your job description for the ${jobTitle} position aligns perfectly with my technical skill set and professional objectives. I'm prepared to hit the ground running.`,
      `The ${jobTitle} position at ${companyName} represents an ideal opportunity to apply my advanced technical knowledge and contribute to cutting-edge projects.`
    ],
    confident: [
      `I am the right candidate for ${companyName}'s ${jobTitle} position. My track record of delivering exceptional results makes me confident I can exceed your expectations.`,
      `I don't just fit the requirements for this ${jobTitle} role—I exceed them. I'm ready to make an immediate impact at ${companyName}.`,
      `This ${jobTitle} position at ${companyName} is a perfect match for my expertise and ambitions. I'm here to make a difference.`
    ]
  };

  const paragraphs = openings[tone] || openings.professional;
  return `<p>${paragraphs[Math.floor(Math.random() * paragraphs.length)]}</p>`;
}

// Generate body paragraph
function generateBodyParagraph(resumeHighlights, jobDescription, tone, jobTitle) {
  let highlights = resumeHighlights ? resumeHighlights.split('\n').filter(h => h.trim()).slice(0, 3) : [];
  
  const bodyTemplates = {
    professional: (highlights, job) => {
      return `<p>Throughout my career, I have demonstrated strong capabilities in${job ? ' the key areas your role requires' : ''}. ${highlights.length > 0 ? 'Key accomplishments include: ' + highlights.map(h => h.replace(/^[-*]\s*/, '').toLowerCase()).join(', ') + '. ' : ''}I am confident these experiences have prepared me to excel in this ${jobTitle} position and drive measurable value for ${job ? 'your organization' : 'the team'}.</p>`;
    },
    friendly: (highlights, job) => {
      return `<p>What I'm most proud of is my ability to combine technical excellence with a collaborative mindset. ${highlights.length > 0 ? highlights.map(h => h.replace(/^[-*]\s*/, '')).join('\n') : 'My experience spans the full spectrum of required competencies.'} I genuinely enjoy working in fast-paced environments where I can learn and grow alongside talented colleagues.</p>`;
    },
    creative: (highlights, job) => {
      return `<p>My approach blends strategic thinking with creative problem-solving. ${highlights.length > 0 ? 'I've driven significant outcomes including: ' + highlights.map(h => h.replace(/^[-*]\s*/, '')).join(', ') + '. ' : ''}I'm excited to bring this innovative mindset to new challenges at your organization and contribute to breakthrough solutions.</p>`;
    },
    technical: (highlights, job) => {
      return `<p>My technical toolkit includes expertise in key areas that align with your requirements. ${highlights.length > 0 ? highlights.map(h => h.replace(/^[-*]\s*/, '')).join(', ') + '. ' : ''}I'm well-positioned to contribute effectively from day one and take on increasingly complex technical challenges.</p>`;
    },
    confident: (highlights, job) => {
      return `<p>I bring a proven ability to deliver results at the highest level. ${highlights.length > 0 ? 'My track record includes: ' + highlights.map(h => h.replace(/^[-*]\s*/, '')).join(', ') + '. ' : ''}I'm ready to make an immediate and lasting impact in this role.</p>`;
    }
  };

  const generator = bodyTemplates[tone] || bodyTemplates.professional;
  return generator(highlights, jobDescription);
}

// Generate closing paragraph
function generateClosingParagraph(whyCompany, companyName, tone) {
  const closings = {
    professional: (why, company) => {
      return `<p>I am deeply interested in joining ${company} and contributing to your team's continued success. ${why ? `${why} ` : ''}I would welcome the opportunity to discuss how my background, skills, and enthusiasm can add value to your organization. Thank you for considering my application. I look forward to connecting with you soon.</p>`;
    },
    friendly: (why, company) => {
      return `<p>I'm genuinely excited about the potential to contribute to ${company}'s mission and grow with your team. ${why ? `${why} ` : ''}I'd love to chat about how we can work together to achieve great things. Thanks for taking time to review my application—I look forward to our conversation!</p>`;
    },
    creative: (why, company) => {
      return `<p>I've been impressed by what ${company} is building and the impact you're making. ${why ? `${why} ` : ''}I'm eager to bring my unique perspective and passion to your team and help drive your next wave of innovation. I look forward to discussing this exciting opportunity.</p>`;
    },
    technical: (why, company) => {
      return `<p>I am confident that my technical expertise and problem-solving abilities make me a strong fit for this role at ${company}. ${why ? `${why} ` : ''}I welcome the opportunity to discuss specific projects and technical challenges. Thank you for your consideration, and I look forward to connecting soon.</p>`;
    },
    confident: (why, company) => {
      return `<p>I am convinced that together, we can achieve remarkable results. I'm ready to bring my A-game to ${company} and make a significant impact. ${why ? `${why} ` : ''}Let's schedule a time to discuss how I can contribute to your success.</p>`;
    }
  };

  const generator = closings[tone] || closings.professional;
  return generator(whyCompany, companyName);
}

// Get closing statement
function getClosingStatement(tone) {
  const statements = {
    professional: 'Sincerely,',
    friendly: 'Best regards,',
    creative: 'With enthusiasm,',
    technical: 'Best regards,',
    confident: 'Warmly,'
  };
  return statements[tone] || 'Sincerely,';
}

// Reset Form
function resetForm() {
  document.querySelectorAll('.form-group input, .form-group textarea, .form-group select').forEach(field => {
    field.value = '';
  });
  
  const preview = document.getElementById('coverLetterPreview');
  preview.innerHTML = `
    <div class="letter-placeholder">
      <p>
        <i class="fa-solid fa-pen-fancy"></i>
        Fill in the form and click "Generate Cover Letter" to see your personalized cover letter here.
      </p>
    </div>
  `;
  
  showNotification('Form cleared', 'info');
}

// Download as PDF
function downloadPDF() {
  const element = document.getElementById('coverLetterPreview');
  
  if (!element.querySelector('.cover-letter-content')) {
    alert('Please generate a cover letter first');
    return;
  }

  // Create a print window
  const printWindow = window.open('', '_blank');
  const fullName = document.getElementById('fullName').value || 'Cover_Letter';
  
  printWindow.document.write(`
    <!DOCTYPE html>
    <html>
    <head>
      <title>${fullName} - Cover Letter</title>
      <style>
        * { margin: 0; padding: 0; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; }
        .letter-header { border-bottom: 2px solid #3498db; padding-bottom: 1rem; margin-bottom: 2rem; }
        .sender-info strong { font-size: 1.1rem; display: block; margin-bottom: 0.5rem; }
        .sender-info p { margin: 0.25rem 0; font-size: 0.9rem; }
        .date { color: #7f8c8d; margin-top: 1rem; font-size: 0.9rem; }
        .recipient-info p { margin: 0.25rem 0; margin-bottom: 1rem; }
        .greeting { font-weight: 600; margin-bottom: 1rem; }
        .letter-body p { margin-bottom: 1rem; text-align: justify; }
        .letter-closing { margin-top: 2rem; }
        .closing-statement { margin-bottom: 1rem; }
        .signature-line { margin-top: 3rem; border-top: 1px solid #2c3e50; padding-top: 1rem; width: 150px; }
        .signature-name { font-weight: 600; }
        a { color: #3498db; text-decoration: none; }
      </style>
    </head>
    <body>
      ${element.innerHTML}
    </body>
    </html>
  `);
  
  printWindow.document.close();
  printWindow.print();
  
  setTimeout(() => {
    printWindow.close();
    showNotification('PDF generated! Use your browser\'s print dialog to save.', 'success');
  }, 250);
}

// Copy to Clipboard
function copyToClipboard() {
  const element = document.getElementById('coverLetterPreview');
  
  if (!element.querySelector('.cover-letter-content')) {
    alert('Please generate a cover letter first');
    return;
  }

  const text = element.innerText;
  navigator.clipboard.writeText(text).then(() => {
    showNotification('Cover letter copied to clipboard!', 'success');
  }).catch(() => {
    alert('Failed to copy. Please try again.');
  });
}

// Print Letter
function printLetter() {
  const element = document.getElementById('coverLetterPreview');
  
  if (!element.querySelector('.cover-letter-content')) {
    alert('Please generate a cover letter first');
    return;
  }

  window.print();
}

// Show Notification
function showNotification(message, type = 'info') {
  const notification = document.createElement('div');
  notification.style.cssText = `
    position: fixed;
    top: 20px;
    right: 20px;
    padding: 1rem 1.5rem;
    background: ${type === 'success' ? '#2ecc71' : type === 'error' ? '#e74c3c' : '#3498db'};
    color: white;
    border-radius: 8px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    z-index: 1000;
    animation: slideIn 0.3s ease;
  `;
  
  notification.textContent = message;
  document.body.appendChild(notification);
  
  setTimeout(() => {
    notification.style.animation = 'slideOut 0.3s ease';
    setTimeout(() => notification.remove(), 300);
  }, 3000);
}

// Add animations
const style = document.createElement('style');
style.textContent = `
  @keyframes slideIn {
    from {
      transform: translateX(400px);
      opacity: 0;
    }
    to {
      transform: translateX(0);
      opacity: 1;
    }
  }
  @keyframes slideOut {
    from {
      transform: translateX(0);
      opacity: 1;
    }
    to {
      transform: translateX(400px);
      opacity: 0;
    }
  }
`;
document.head.appendChild(style);
