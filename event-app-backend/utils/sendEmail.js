const nodemailer = require('nodemailer');

const transporter = nodemailer.createTransport({
  service: 'gmail',
  auth: {
    user: process.env.GMAIL_USER,
    pass: process.env.GMAIL_APP_PASSWORD
  }
});

const sendEmail = async (to, subject, text) => {
  await transporter.sendMail({
    from: process.env.GMAIL_USER,
    to,
    subject,
    text
  });
};

module.exports = sendEmail;