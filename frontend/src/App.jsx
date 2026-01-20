import { useState } from "react";
import axios from "axios";
import "./index.css";

function App() {
  const [file, setFile] = useState(null); //Without useState, React forgets everything after rendering
  const [result, setResult] = useState("");

  const handleFileChange = (e) => {
    setFile(e.target.files[0]);
  };

  const handleAnalyze = async () => {
    if (!file) {
      alert("Select a file first");
      return;
    }

    if (file.type !== "application/pdf") {
      alert("Only PDF files are allowed");
      return;
    }

    if (file.size > 50 * 1024 * 1024) {
      alert("File size must be under 50 MB");
      return;
    }


    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await axios.post(
        "http://localhost:5000/upload",
        formData
      );
      setResult(JSON.stringify(res.data, null, 2));
    } catch (err) {
      console.error(err);
      alert("Upload failed");
    }
  };

  return (
    <div className="container">
      <h1>FinSight AI – Phase 1</h1>

      <input type="file" onChange={handleFileChange} />
      <button onClick={handleAnalyze}>Analyze</button>

      <pre>{result}</pre>
    </div>
  );
}

export default App;
