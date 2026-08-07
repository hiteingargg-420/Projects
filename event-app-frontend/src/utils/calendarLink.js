function formatGoogleDate(date) {
  return new Date(date).toISOString().replace(/-|:|\.\d+/g, '');
}

export function getGoogleCalendarLink(event) {
  const start = formatGoogleDate(event.date);
  const endDate = new Date(event.date);
  endDate.setHours(endDate.getHours() + 2);
  const end = formatGoogleDate(endDate);

  const params = new URLSearchParams({
    action: 'TEMPLATE',
    text: event.title,
    dates: `${start}/${end}`,
    details: event.description,
    location: event.location
  });

  return `https://calendar.google.com/calendar/render?${params.toString()}`;
}