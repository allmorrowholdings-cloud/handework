export const services = [
  { code: "01", name: "Plumbing", note: "Stop leaks and fit new taps.", image: "plumbing" },
  { code: "02", name: "Carpentry", note: "Fix doors or commission furniture.", image: "carpentry" },
  { code: "03", name: "Welding", note: "Repair gates or build custom metalwork.", image: "welding" },
  { code: "04", name: "Painting", note: "Refresh rooms and exterior walls.", image: "painting" },
  { code: "05", name: "Masonry", note: "Build block walls and patch plaster.", image: "masonry" },
  { code: "06", name: "Tailoring", note: "Alter clothes or get a custom fit.", image: "tailoring" },
  { code: "07", name: "Hairdressing", note: "Book braids, cuts, or styling.", image: "hair-beauty" },
  { code: "08", name: "Makeup artist", note: "Get makeup for events and photos.", image: "makeup" },
  { code: "09", name: "Catering", note: "Feed your guests without the cooking.", image: "food-events" },
];

export const serviceNames = [...services.map(service => service.name), "Electrical", "Digital design"];
