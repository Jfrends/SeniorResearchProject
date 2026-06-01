import React, { useEffect, useState, useContext } from "react";
import {
  Box,
  Typography,
  Button,
  CircularProgress,
  Dialog,
  DialogTitle,
  DialogContent,
  TextField,
  DialogActions,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  IconButton,
} from "@mui/material";
import FolderIcon from "@mui/icons-material/Folder";
import InsertDriveFileIcon from "@mui/icons-material/InsertDriveFile";
import UploadFileIcon from "@mui/icons-material/UploadFile";
import DeleteIcon from "@mui/icons-material/Delete";
import { AuthContext } from "../contexts/AuthContext";
import { Navigate } from "react-router-dom";

export default function MyFiles() {
  const { token, userId } = useContext(AuthContext);

  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(true);

  const [openFolderModal, setOpenFolderModal] = useState(false);
  const [folderName, setFolderName] = useState("");

  const [selectedFile, setSelectedFile] = useState(null);
  const [uploading, setUploading] = useState(false);

  const [currentPath, setCurrentPath] = useState("/");

  const [selectedItem, setSelectedItem] = useState(null);
  const [fileText, setFileText] = useState("");
  const [textLoading, setTextLoading] = useState(false);

  // ---------------- SEARCH + ASK ----------------
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState([]);
  const [isSearching, setIsSearching] = useState(false);
  const [searchLoading, setSearchLoading] = useState(false);

  const [askAnswer, setAskAnswer] = useState("");
  const [askSources, setAskSources] = useState([]);
  const [askLoading, setAskLoading] = useState(false);

  if (!userId) return <Navigate to="/login" replace />;

  // ---------------- FETCH FILES ----------------
  const fetchFiles = async () => {
    setLoading(true);
    try {
      const res = await fetch(
        `${import.meta.env.VITE_API_BASE_URL}/files`,
        { headers: { Authorization: `Bearer ${token}` } }
      );

      if (!res.ok) throw new Error("Failed to fetch files");

      const data = await res.json();
      setFiles(data.filter((f) => f.folder_path === currentPath));
    } catch (err) {
      console.error(err);
      setFiles([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchFiles();
    setSelectedItem(null);
    setFileText("");

    setIsSearching(false);
    setSearchResults([]);
    setSearchQuery("");

    setAskAnswer("");
    setAskSources([]);
  }, [currentPath]);

  // ---------------- SEARCH ----------------
  const handleSearch = async () => {
    if (!searchQuery.trim()) return;

    setSearchLoading(true);
    setIsSearching(true);
    setAskAnswer("");

    try {
      const res = await fetch(
        `${import.meta.env.VITE_API_BASE_URL}/semantic-search?query=${encodeURIComponent(
          searchQuery
        )}&current_path=${encodeURIComponent(currentPath)}&owner_id=${userId}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );

      if (!res.ok) throw new Error("Search failed");

      const data = await res.json();
      setSearchResults(data);
      setAskAnswer("");
    } catch (err) {
      console.error(err);
      setSearchResults([]);
    } finally {
      setSearchLoading(false);
    }
  };

  // ---------------- ASK AI ----------------
  const handleAsk = async () => {
    if (!searchQuery.trim()) return;

    setAskLoading(true);
    setIsSearching(true);
    setAskAnswer("");
    setAskSources([]);
    setSearchResults([]);

    try {
      const res = await fetch(
        `${import.meta.env.VITE_API_BASE_URL}/ask`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            query: searchQuery,
            current_path: currentPath,
            owner_id: userId,
          }),
        }
      );

      if (!res.ok) throw new Error("Ask failed");

      const data = await res.json();

      setAskAnswer(data.answer);
      setAskSources(data.sources || []);
    } catch (err) {
      console.error(err);
      setAskAnswer("Error generating answer.");
    } finally {
      setAskLoading(false);
    }
  };

  const clearSearch = () => {
    setIsSearching(false);
    setSearchResults([]);
    setSearchQuery("");
    setAskAnswer("");
    setAskSources([]);
  };

  // ---------------- FOLDER OPS ----------------
  const handleCreateFolder = async () => {
    if (!folderName.trim()) return;

    try {
      const res = await fetch(
        `${import.meta.env.VITE_API_BASE_URL}/users/${userId}/folders`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            filename: folderName,
            path: currentPath,
          }),
        }
      );

      if (!res.ok) throw new Error("Create folder failed");

      setFolderName("");
      setOpenFolderModal(false);
      fetchFiles();
    } catch (err) {
      console.error(err);
    }
  };

  const enterFolder = (name) => setCurrentPath(`${currentPath}${name}/`);

  const goUp = () => {
    if (currentPath === "/") return;
    const parts = currentPath.split("/").filter(Boolean);
    parts.pop();
    setCurrentPath("/" + parts.join("/") + (parts.length ? "/" : ""));
  };

  // ---------------- UPLOAD ----------------
  const handleUploadFile = async () => {
    if (!selectedFile) return;

    setUploading(true);
    try {
      const formData = new FormData();
      formData.append("file", selectedFile);
      formData.append("path", currentPath);

      const res = await fetch(
        `${import.meta.env.VITE_API_BASE_URL}/users/${userId}/files`,
        {
          method: "POST",
          headers: { Authorization: `Bearer ${token}` },
          body: formData,
        }
      );

      if (!res.ok) throw new Error("Upload failed");

      setSelectedFile(null);
      fetchFiles();
    } catch (err) {
      console.error(err);
    } finally {
      setUploading(false);
    }
  };

  // ---------------- DELETE ----------------
  const handleDelete = async (item) => {
    if (!window.confirm(`Delete "${item.filename}"?`)) return;

    const endpoint = item.is_folder
      ? `/folders/${item.id}`
      : `/files/${item.id}`;

    try {
      const res = await fetch(
        `${import.meta.env.VITE_API_BASE_URL}${endpoint}`,
        {
          method: "DELETE",
          headers: { Authorization: `Bearer ${token}` },
        }
      );

      if (!res.ok) throw new Error("Delete failed");

      fetchFiles();

      if (selectedItem?.id === item.id) {
        setSelectedItem(null);
        setFileText("");
      }
    } catch (err) {
      console.error(err);
    }
  };

  // ---------------- FILE PREVIEW ----------------
  const handleSelectFile = async (item) => {
    if (item.is_folder) return;

    const fileId = item.id || item.file_id;

    setSelectedItem(item);
    setTextLoading(true);
    setFileText("");

    try {
      const res = await fetch(
        `${import.meta.env.VITE_API_BASE_URL}/files/${fileId}/text`,
        { headers: { Authorization: `Bearer ${token}` } }
      );

      if (!res.ok) throw new Error("No preview");

      const text = await res.text();
      setFileText(text || "");
    } catch {
      setFileText("Unable to load file preview.");
    } finally {
      setTextLoading(false);
    }
  };

  const displayFiles = isSearching ? searchResults : files;

  // ---------------- UI ----------------
  return (
    <Box sx={{ p: 3, display: "flex", flexDirection: "column", height: "100%" }}>
      <Typography variant="h5" gutterBottom>
        My Files
      </Typography>

      {/* CONTROLS */}
      <Box sx={{ display: "flex", gap: 2, mb: 2, flexWrap: "wrap" }}>
        <Button variant="contained" onClick={() => setOpenFolderModal(true)}>
          Create Folder
        </Button>

        <Button onClick={goUp} disabled={currentPath === "/"}>
          Back
        </Button>

        <Button component="label" variant="outlined" startIcon={<UploadFileIcon />}>
          Select File
          <input
            hidden
            type="file"
            onChange={(e) => setSelectedFile(e.target.files[0])}
          />
        </Button>

        <Button
          onClick={handleUploadFile}
          disabled={!selectedFile || uploading}
          variant="contained"
          color="success"
        >
          {uploading ? "Uploading..." : "Upload"}
        </Button>

        {/* SEARCH / ASK */}
        <TextField
          size="small"
          placeholder="Search or ask your files..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSearch()}
        />

        <Button variant="outlined" onClick={handleSearch}>
          Search
        </Button>

        <Button variant="contained" onClick={handleAsk}>
          Ask AI
        </Button>

        {isSearching && (
          <Button color="secondary" onClick={clearSearch}>
            Clear
          </Button>
        )}
      </Box>

      <Typography sx={{ mb: 1 }}>Path: {currentPath}</Typography>

      {/* MAIN LAYOUT */}
      <Box sx={{ display: "flex", gap: 2, height: "70vh", minHeight: 0 }}>
        {/* LEFT */}
        <Box sx={{ flex: 1, overflowY: "auto" }}>
          {loading || searchLoading || askLoading ? (
            <CircularProgress />
          ) : (
            <List>
              {displayFiles.map((item) => (
                <ListItem
                  key={item.id || item.file_id}
                  button
                  selected={selectedItem?.id === item.id}
                  onClick={() =>
                    item.is_folder
                      ? enterFolder(item.filename)
                      : handleSelectFile(item)
                  }
                  secondaryAction={
                    !isSearching && (
                      <IconButton
                        edge="end"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDelete(item);
                        }}
                        sx={{ color: "red" }}
                      >
                        <DeleteIcon fontSize="small" />
                      </IconButton>
                    )
                  }
                >
                  <ListItemIcon>
                    {item.is_folder ? <FolderIcon /> : <InsertDriveFileIcon />}
                  </ListItemIcon>
                  <ListItemText primary={item.filename} />
                </ListItem>
              ))}
            </List>
          )}
        </Box>

        {/* RIGHT PANEL */}
        <Box
          sx={{
            flex: 2,
            border: "1px solid #ccc",
            borderRadius: 2,
            p: 2,
            bgcolor: "#fafafa",
            overflowY: "auto",
            fontFamily: "monospace",
            whiteSpace: "pre-wrap",
          }}
        >
          {/* ASK MODE */}
          {askAnswer ? (
            <>
              <Typography variant="subtitle2" gutterBottom>
                AI Answer
              </Typography>

              <Typography sx={{ mb: 2 }}>{askAnswer}</Typography>

              {askSources.length > 0 && (
                <>
                  <Typography variant="subtitle2">Sources</Typography>
                  {askSources.map((s, i) => (
                    <Typography key={i} variant="caption" display="block">
                      📄 {s.filename}
                    </Typography>
                  ))}
                </>
              )}
            </>
          ) : !selectedItem ? (
            <Typography color="text.secondary">
              Select a file or ask a question
            </Typography>
          ) : textLoading ? (
            <CircularProgress />
          ) : (
            <>
              <Typography variant="subtitle2">
                {selectedItem.filename}
              </Typography>
              <Typography>{fileText}</Typography>
            </>
          )}
        </Box>
      </Box>

      {/* FOLDER MODAL */}
      <Dialog open={openFolderModal} onClose={() => setOpenFolderModal(false)}>
        <DialogTitle>Create Folder</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            fullWidth
            label="Folder name"
            value={folderName}
            onChange={(e) => setFolderName(e.target.value)}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenFolderModal(false)}>Cancel</Button>
          <Button onClick={handleCreateFolder} variant="contained">
            Create
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}