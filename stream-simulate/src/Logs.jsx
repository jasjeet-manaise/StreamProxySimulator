import PropTypes from "prop-types";
import { useState, useEffect } from "react";

const Log = ({ onClose }) => {
  const [logs, setLogs] = useState([]);

  useEffect(() => {
    const ws = new WebSocket(import.meta.env.VITE_WS_URL);

    ws.onmessage = (event) => {
      setLogs((prevLogs) => [...prevLogs, event.data]);
    };

    ws.onclose = () => {
      console.log("WebSocket connection closed.");
    };

    return () => {
      ws.close();
    };
  }, []);

  return (
    <div className="log-overlay" onClick={onClose}>
      <div className="log-content" onClick={(e) => e.stopPropagation()}>
        <div className="logsHeader">
          <span>Logs</span>
          <button
            className="btn-close close-btn-custom"
            onClick={onClose}
          ></button>
        </div>
        <div className="logs-msgs">
          <ul>
            {logs.map((log, index) => (
              <li
                style={{
                  listStyle: "none",
                  textAlign: "left",
                  fontSize: "15px",
                  color: "darkgreen",
                }}
                key={index}
              >
                {">"} {log}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
};

Log.propTypes = {
  onClose: PropTypes.func.isRequired,
};

export default Log;
