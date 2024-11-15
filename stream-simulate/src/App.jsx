import { useState } from "react";
import Logs from "./Logs";
import "./App.css";
import CopyableInput from "./CopyableInput";

function App() {
  const [showLog, setShowLog] = useState(false);
  const [selectedSimulation, setSelectedSimulation] = useState(null);

  const handleShowLog = () => {
    setShowLog(true);
  };

  const handleCloseLog = () => {
    setShowLog(false);
  };

  const [data, setData] = useState({
    url: "",
    simulate: "audio",
    delay: 0,
    segments: 0,
    delayAfterSegments: 0,
    delayDuration: 0,
    stuckRecoveryTimeout: 0,
    dropAfterPlaylists: 0,
    segmentFailureFrequency: 0,
    segmentFailureCode: 404,
    playlistStickThreshold: 0,
  });

  const [generatedUrl, setGenerateUrl] = useState("");

  const onChange = (event) => {
    const { name, value, type, checked } = event.target;
    const newValue =
      type === "checkbox"
        ? checked
        : [
            "delay",
            "segments",
            "delayAfterSegments",
            "stuckRecoveryTimeout",
            "dropAfterPlaylists",
            "segmentFailureFrequency",
            "playlistStickThreshold",
            "segmentFailureCode",
          ].includes(name)
        ? parseInt(value)
        : value;

    setData((prev) => ({
      ...prev,
      [name]: newValue,
    }));
  };

  const onSubmit = async (event) => {
    event.preventDefault();
    if (!selectedSimulation) {
      alert("Please select a simulation type before starting the simulation.");
      return;
    }

    const filteredData = { url: data.url, simulate: selectedSimulation };

    switch (selectedSimulation) {
      case "delayAudio":
        filteredData.delay = data.delay;
        filteredData.segments = data.segments;
        break;
      case "stuckPlaylist":
        filteredData.playlistStickThreshold = data.playlistStickThreshold;
        filteredData.stuckRecoveryTimeout = data.stuckRecoveryTimeout;
        break;
      case "dropPacket":
        filteredData.dropAfterPlaylists = data.dropAfterPlaylists;
        break;
      case "segmentFailure":
        filteredData.segmentFailureFrequency = data.segmentFailureFrequency;
        filteredData.segmentFailureCode = data.segmentFailureCode;
        break;
      default:
        break;
    }

    console.log("Filtered data to send:", filteredData);

    // Make the request with the filtered data
    const res = await fetch(import.meta.env.VITE_BACKEND_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(filteredData),
    });

    const response = await res.json();
    setGenerateUrl(response.generatedUrl);
  };

  const handleSimulationClick = (simulationType) => {
    setSelectedSimulation(simulationType);
  };

  return (
    <div className="container mt-4">
      <div className="header">
        <img src="/xperi.jpg" alt="Brand Logo" className="brandLogo" />
      </div>
      <div className="header">
        <h1 className="mb-4">Stream Proxy</h1>
      </div>

      <form onSubmit={onSubmit}>
        <div className="mb-3">
          <label htmlFor="url" className="form-label">
            URL
          </label>
          <input
            type="url"
            name="url"
            value={data.url}
            onChange={onChange}
            className="form-control"
            id="url"
            placeholder="URL"
            required
          />
        </div>

        {/* Simulation Types */}
        <div className="mt-4">
          <h5>Simulation Types</h5>

          {/* Audio Delay Settings */}
          <div
            className="simulation-option"
            style={{
              cursor: "pointer",
              marginBottom: "10px",
              backgroundColor: "#f9f9f9",
              padding: "10px",
              borderRadius: "8px",
              border: "1px solid #ddd",
            }}
            onClick={() => handleSimulationClick("delayAudio")}
          >
            <h6 className="simulation-title">Audio Delay Settings</h6>
            {selectedSimulation === "delayAudio" && (
              <div
                className="simulation-options-box"
                style={{
                  backgroundColor: "#f4f4f4",
                  padding: "15px",
                  borderRadius: "8px",
                }}
              >
                <div className="form-group row mb-3">
                  <label htmlFor="delay" className="col-sm-2 col-form-label">
                    Delay (seconds)
                  </label>
                  <div className="col-sm-10">
                    <input
                      name="delay"
                      value={data.delay}
                      onChange={onChange}
                      type="number"
                      className="form-control"
                      id="delay"
                      placeholder="Enter delay in seconds"
                    />
                  </div>
                </div>
                <div className="form-group row mb-3">
                  <label htmlFor="segments" className="col-sm-2 col-form-label">
                    Segments
                  </label>
                  <div className="col-sm-10">
                    <input
                      name="segments"
                      value={data.segments}
                      onChange={onChange}
                      type="number"
                      className="form-control"
                      id="segments"
                      placeholder="Enter number of segments after delay should occur"
                    />
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Stuck Playlist Simulation */}
          <div
            className="simulation-option"
            style={{
              cursor: "pointer",
              marginBottom: "10px",
              backgroundColor: "#f9f9f9",
              padding: "10px",
              borderRadius: "8px",
              border: "1px solid #ddd",
            }}
            onClick={() => handleSimulationClick("stuckPlaylist")}
          >
            <h6 className="simulation-title">Stuck Playlist Simulation</h6>
            {selectedSimulation === "stuckPlaylist" && (
              <div
                className="simulation-options-box"
                style={{
                  backgroundColor: "#f4f4f4",
                  padding: "15px",
                  borderRadius: "8px",
                }}
              >
                <div className="form-group row mb-3 mt-2">
                  <label
                    htmlFor="playlistStickThreshold"
                    className="col-sm-2 col-form-label"
                  >
                    Playlist Stick Threshold
                  </label>
                  <div className="col-sm-10">
                    <input
                      name="playlistStickThreshold"
                      value={data.playlistStickThreshold}
                      onChange={onChange}
                      type="number"
                      className="form-control"
                      id="playlistStickThreshold"
                      placeholder="Enter playlist stick threshold"
                    />
                  </div>
                </div>
                <div className="form-group row mb-3 mt-2">
                  <label
                    htmlFor="stuckRecoveryTimeout"
                    className="col-sm-2 col-form-label"
                  >
                    Stuck Recovery Timeout
                  </label>
                  <div className="col-sm-10">
                    <input
                      name="stuckRecoveryTimeout"
                      value={data.stuckRecoveryTimeout}
                      onChange={onChange}
                      type="number"
                      className="form-control"
                      id="stuckRecoveryTimeout"
                      placeholder="Enter timeout for stuck playlist recovery"
                    />
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Packet Drop Simulation */}
          <div
            className="simulation-option"
            style={{
              cursor: "pointer",
              marginBottom: "10px",
              backgroundColor: "#f9f9f9",
              padding: "10px",
              borderRadius: "8px",
              border: "1px solid #ddd",
            }}
            onClick={() => handleSimulationClick("dropPacket")}
          >
            <h6 className="simulation-title">Packet Drop Simulation</h6>
            {selectedSimulation === "dropPacket" && (
              <div
                className="simulation-options-box"
                style={{
                  backgroundColor: "#f4f4f4",
                  padding: "15px",
                  borderRadius: "8px",
                }}
              >
                <div className="form-group row mb-3">
                  <label
                    htmlFor="dropAfterPlaylists"
                    className="col-sm-2 col-form-label"
                  >
                    Drop After Playlists
                  </label>
                  <div className="col-sm-10">
                    <input
                      name="dropAfterPlaylists"
                      value={data.dropAfterPlaylists}
                      onChange={onChange}
                      type="number"
                      className="form-control"
                      id="dropAfterPlaylists"
                      placeholder="Enter number of playlists before dropping packets"
                    />
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Segment Failure Simulation */}
          <div
            className="simulation-option"
            style={{
              cursor: "pointer",
              marginBottom: "10px",
              backgroundColor: "#f9f9f9",
              padding: "10px",
              borderRadius: "8px",
              border: "1px solid #ddd",
            }}
            onClick={() => handleSimulationClick("segmentFailure")}
          >
            <h6 className="simulation-title">Segment Failure Simulation</h6>
            {selectedSimulation === "segmentFailure" && (
              <div
                className="simulation-options-box"
                style={{
                  backgroundColor: "#f4f4f4",
                  padding: "15px",
                  borderRadius: "8px",
                }}
              >
                <div className="form-group row mb-3">
                  <label
                    htmlFor="segmentFailureFrequency"
                    className="col-sm-2 col-form-label"
                  >
                    Segment Failure Frequency
                  </label>
                  <div className="col-sm-10">
                    <input
                      name="segmentFailureFrequency"
                      value={data.segmentFailureFrequency}
                      onChange={onChange}
                      type="number"
                      className="form-control"
                      id="segmentFailureFrequency"
                      placeholder="Enter frequency of segment failures"
                    />
                  </div>
                </div>
                <div className="form-group row mb-3">
                  <label
                    htmlFor="segmentFailureCode"
                    className="col-sm-2 col-form-label"
                  >
                    Segment Failure Code
                  </label>
                  <div className="col-sm-10">
                    <input
                      name="segmentFailureCode"
                      value={data.segmentFailureCode}
                      onChange={onChange}
                      type="number"
                      className="form-control"
                      id="segmentFailureCode"
                      placeholder="Enter HTTP code for segment failure"
                    />
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        <button type="submit" className="btn btn-success mt-3">
          Simulate
        </button>
      </form>

      {generatedUrl && (
        <CopyableInput url={generatedUrl} handleShowLog={handleShowLog} />
      )}
      {showLog && <Logs onClose={handleCloseLog} />}
    </div>
  );
}

export default App;
