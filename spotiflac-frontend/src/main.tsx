import RootLayout from "@/layouts/RootLayout";
import Bulk from "@/pages/Bulk";
import Home from "@/pages/Home";
import "@/styles/main.css";
import "@fontsource-variable/inter";
import "@fontsource/playfair-display/400.css";
import "@fontsource/playfair-display/600.css";
import "@fontsource/playfair-display/700.css";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Route, Routes } from "react-router-dom";

createRoot(document.getElementById("root")!).render(
  <BrowserRouter>
    <Routes>
      <Route path="/" element={<RootLayout />}>
        <Route index element={<Home />} />
        <Route path="bulk" element={<Bulk />} />
      </Route>
    </Routes>
  </BrowserRouter>,
);
