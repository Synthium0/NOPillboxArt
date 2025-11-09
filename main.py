import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import json, copy, os, random

# ----------------- PILLBOX GENERATOR -----------------
def generate_pillboxes_from_image(
    art_path, skeleton_path, output_json, center_x, center_y, center_z,
    threshold, spacing, max_pillboxes, generation_scale=1.0, replace_existing=True
):
    if not os.path.exists(art_path):
        messagebox.showerror("Error", f"{art_path} not found!")
        return

    img = Image.open(art_path).convert("L")
    width, height = img.size

    # Resize according to generation scale (art_scale only)
    new_w = max(1, int(width * generation_scale))
    new_h = max(1, int(height * generation_scale))
    resized = img.resize((new_w, new_h), Image.NEAREST)
    bw_img = resized.point(lambda p: 255 if p > threshold else 0, '1')
    pixels = bw_img.load()

    # Collect pill positions
    pill_positions = [(x, y) for y in range(new_h) for x in range(new_w) if pixels[x, y] == 255]

    # Cap to max_pillboxes
    if len(pill_positions) > max_pillboxes:
        pill_positions = random.sample(pill_positions, max_pillboxes)

    buildings = []
    pillbox_template = {
        "type": "pillbox",
        "faction": "",
        "UniqueName": "",
        "globalPosition": {"x": 0, "y": 0, "z": 0},
        "rotation": {"x": 0.0, "y": 0.0, "z": 0.0, "w": 0.0},
        "CaptureStrength": {"IsOverride": False, "Value": 2.0},
        "CaptureDefense": {"IsOverride": False, "Value": 200.0},
        "unitCustomID": "",
        "spawnTiming": "",
        "capturable": False,
        "Airbase": "",
        "factoryOptions": {"productionType": "", "productionTime": 900.0},
        "placementOffset": 0.0
    }

    offset_x = center_x - (new_w * spacing) / 2
    offset_z = center_z - (new_h * spacing) / 2

    for counter, (x, y) in enumerate(pill_positions):
        pb = copy.deepcopy(pillbox_template)
        pb["UniqueName"] = f"pillbox_{counter}"
        pb["globalPosition"]["x"] = offset_x + x * spacing
        pb["globalPosition"]["y"] = center_y
        pb["globalPosition"]["z"] = offset_z + (new_h - y - 1) * spacing
        buildings.append(pb)

    # Print leftmost and rightmost pillbox X
    if buildings:
        xs = [b["globalPosition"]["x"] for b in buildings]
        print(f"Leftmost pillbox X: {min(xs):.2f}, Rightmost pillbox X: {max(xs):.2f}")

    # Load skeleton JSON
    if os.path.exists(skeleton_path):
        with open(skeleton_path, "r") as f:
            mission_json = json.load(f)
    else:
        mission_json = {"buildings": []}

    mission_json["buildings"] = buildings if replace_existing else mission_json.get("buildings", []) + buildings

    with open(output_json, "w") as f:
        json.dump(mission_json, f, indent=4)

    messagebox.showinfo("Success", f"Generated {len(buildings)} pillboxes → {output_json}")

# ----------------- GUI -----------------
class MapBuilderApp:
    MAP_WORLD_SCALE = 80000 / 3000  # Change 1024 to your map.png width in pixels

    def __init__(self, root):
        self.root = root
        self.root.title("Pillbox Map Builder")
        self.root.geometry("1200x800")

        # Canvas
        self.canvas = tk.Canvas(root, bg="#2b2b2b")
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.canvas.bind("<ButtonPress-1>", self.start_drag_art)
        self.canvas.bind("<B1-Motion>", self.drag_art)
        self.canvas.bind("<ButtonRelease-1>", self.stop_drag_art)
        self.canvas.bind("<ButtonPress-3>", self.start_pan)
        self.canvas.bind("<B3-Motion>", self.do_pan)
        self.canvas.bind("<MouseWheel>", self.zoom)
        self.canvas.bind("<Button-4>", lambda e:self.zoom(e, True))
        self.canvas.bind("<Button-5>", lambda e:self.zoom(e, False))

        # Sidebar
        sidebar = tk.Frame(root)
        sidebar.pack(side=tk.RIGHT, fill=tk.Y, padx=10, pady=10)

        self.threshold_var = tk.IntVar(value=35)
        self.spacing_var = tk.DoubleVar(value=10.0)
        self.max_var = tk.IntVar(value=3500)
        self.altitude_var = tk.DoubleVar(value=3.0)

        def add_field(label, var, row):
            tk.Label(sidebar, text=label).grid(row=row, column=0, sticky="w")
            tk.Entry(sidebar, textvariable=var, width=10).grid(row=row, column=1, sticky="w")

        add_field("Threshold", self.threshold_var, 0)
        add_field("Spacing", self.spacing_var, 1)
        add_field("Max Pillboxes", self.max_var, 2)
        add_field("Altitude (Y)", self.altitude_var, 3)

        tk.Button(sidebar, text="Import Art Image", command=self.import_art).grid(row=4,column=0,columnspan=2,pady=10,sticky="ew")
        tk.Label(sidebar,text="Scale Art:").grid(row=5,column=0,columnspan=2,sticky="w")
        tk.Button(sidebar,text="+",command=lambda:self.scale_art(1.1)).grid(row=6,column=0,sticky="ew")
        tk.Button(sidebar,text="-",command=lambda:self.scale_art(0.9)).grid(row=6,column=1,sticky="ew")
        tk.Button(sidebar,text="Build",command=self.build).grid(row=7,column=0,columnspan=2,pady=15,sticky="ew")
        tk.Label(sidebar,text="Drag art: Left Click\nPan map: Right Click\nZoom: Scroll Wheel",justify="left").grid(row=8,column=0,columnspan=2,pady=10)

        # Images
        self.map_img = Image.open("map.png") if os.path.exists("map.png") else None
        self.map_tk = None
        self.map_obj = None
        self.art_img = None
        self.art_tk = None
        self.art_obj = None
        self.art_scale = 1.0
        self.dragging_art = False
        self.drag_start = (0,0)
        self.pan_start = None
        self.zoom_level = 1.0

        # Art map-relative coords
        self.art_map_x = 0
        self.art_map_y = 0

        if self.map_img:
            self.update_map_image()

    # ---------------- MAP ----------------
    def update_map_image(self, anchor=None):
        if not self.map_img:
            return
        old_w = self.map_tk.width() if self.map_tk else self.map_img.width
        old_h = self.map_tk.height() if self.map_tk else self.map_img.height

        w,h = int(self.map_img.width*self.zoom_level), int(self.map_img.height*self.zoom_level)
        self.map_tk = ImageTk.PhotoImage(self.map_img.resize((w,h), Image.Resampling.LANCZOS))

        if self.map_obj is None:
            self.map_obj = self.canvas.create_image(self.canvas.winfo_width()/2,self.canvas.winfo_height()/2,image=self.map_tk,anchor="center")
        else:
            if anchor is None:
                anchor = (self.canvas.winfo_width()/2,self.canvas.winfo_height()/2)
            coords = self.canvas.coords(self.map_obj)
            old_map_x, old_map_y = coords
            dx = (old_map_x - anchor[0])/old_w
            dy = (old_map_y - anchor[1])/old_h
            new_map_x = anchor[0] + dx * w
            new_map_y = anchor[1] + dy * h
            self.canvas.coords(self.map_obj,new_map_x,new_map_y)
            self.canvas.itemconfig(self.map_obj,image=self.map_tk)

        self.canvas.tag_lower(self.map_obj)
        self.update_art_position()

    # ---------------- ART ----------------
    def import_art(self):
        path = filedialog.askopenfilename(filetypes=[("Images","*.png;*.jpg;*.jpeg")])
        if not path:
            return
        self.art_img = Image.open(path)
        self.art_scale = 1.0
        self.art_map_x = 0
        self.art_map_y = 0
        self.update_art_position()

    def scale_art(self,factor):
        self.art_scale *= factor
        self.update_art_position()

    def update_art_position(self):
        if not self.art_img:
            return
        # GUI size (affected by zoom for display)
        w = max(1,int(self.art_img.width*self.art_scale*self.zoom_level))
        h = max(1,int(self.art_img.height*self.art_scale*self.zoom_level))
        self.art_tk = ImageTk.PhotoImage(self.art_img.resize((w,h), Image.Resampling.LANCZOS))
        if self.art_obj is None:
            self.art_obj = self.canvas.create_image(self.canvas.winfo_width()/2,self.canvas.winfo_height()/2,image=self.art_tk,anchor="center")
            self.canvas.tag_raise(self.art_obj)
        else:
            self.canvas.itemconfig(self.art_obj,image=self.art_tk)

        if self.map_obj:
            map_coords = self.canvas.coords(self.map_obj)
            canvas_x = map_coords[0] + self.art_map_x * self.zoom_level
            canvas_y = map_coords[1] + self.art_map_y * self.zoom_level
            self.canvas.coords(self.art_obj,canvas_x,canvas_y)

        # --- PRINT WORLD COORDS WITH OFFSETS ---
        world_x = self.art_map_x * self.MAP_WORLD_SCALE
        world_y = self.altitude_var.get()
        world_z = -self.art_map_y * self.MAP_WORLD_SCALE
        print(f"Art midpoint in world coords: ({world_x:.2f}, {world_y:.2f}, {world_z:.2f})")

    # ---------------- DRAG ----------------
    def start_drag_art(self,event):
        if not self.art_obj:
            return
        clicked = self.canvas.find_closest(event.x,event.y)
        if clicked and clicked[0]==self.art_obj:
            self.dragging_art=True
            self.drag_start=(event.x,event.y)

    def drag_art(self,event):
        if self.dragging_art:
            dx = (event.x-self.drag_start[0])/self.zoom_level
            dy = (event.y-self.drag_start[1])/self.zoom_level
            self.art_map_x += dx
            self.art_map_y += dy
            self.update_art_position()
            self.drag_start=(event.x,event.y)

    def stop_drag_art(self,event):
        self.dragging_art=False

    # ---------------- PAN ----------------
    def start_pan(self,event):
        self.pan_start=(event.x,event.y)

    def do_pan(self,event):
        if not self.pan_start:
            return
        dx=event.x-self.pan_start[0]
        dy=event.y-self.pan_start[1]
        self.canvas.move("all",dx,dy)
        self.pan_start=(event.x,event.y)

    # ---------------- ZOOM ----------------
    def zoom(self,event,linux_scroll=None):
        factor = 1.2 if (event.delta>0 if linux_scroll is None else linux_scroll) else 0.8
        anchor = (self.canvas.canvasx(event.x), self.canvas.canvasy(event.y))
        self.zoom_level *= factor
        self.update_map_image(anchor=anchor)

    # ---------------- BUILD ----------------
    def build(self):
        if not self.art_img:
            messagebox.showerror("Error","No art imported!")
            return

        # World coords + offsets
        world_x = self.art_map_x * self.MAP_WORLD_SCALE
        world_y = self.altitude_var.get()
        world_z = -self.art_map_y * self.MAP_WORLD_SCALE

        # Only art_scale affects generation
        generation_scale = self.art_scale

        generate_pillboxes_from_image(
            art_path=self.art_img.filename,
            skeleton_path="Blank.json",
            output_json="Output.json",
            center_x=world_x,
            center_y=world_y,
            center_z=world_z,
            threshold=self.threshold_var.get(),
            spacing=self.spacing_var.get(),
            max_pillboxes=self.max_var.get(),
            generation_scale=generation_scale,
            replace_existing=True
        )

# ---------------- MAIN ----------------
if __name__=="__main__":
    root=tk.Tk()
    app=MapBuilderApp(root)
    root.mainloop()
