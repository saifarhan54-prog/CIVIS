"""
Generate synthetic CCTV-style demo videos for testing
"""
import cv2
import numpy as np
from pathlib import Path
import random
import subprocess
import imageio_ffmpeg

OUTPUT_DIR = Path(__file__).parent.parent / "data" / "videos"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

class MovingObject:
    """Simulated moving object"""
    def __init__(self, obj_type, start_pos, velocity, size, color):
        self.type = obj_type
        self.pos = list(start_pos)
        self.velocity = velocity
        self.size = size
        self.color = color
    
    def update(self):
        self.pos[0] += self.velocity[0]
        self.pos[1] += self.velocity[1]
    
    def draw(self, frame):
        x, y = int(self.pos[0]), int(self.pos[1])
        w, h = self.size
        
        if self.type == "person":
            # Draw person as rectangle with head
            cv2.rectangle(frame, (x, y), (x+w, y+h), self.color, -1)
            cv2.circle(frame, (x+w//2, y-10), 8, self.color, -1)
            cv2.putText(frame, "P", (x+5, y+h-5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,255), 1)
        elif self.type == "vehicle":
            # Draw vehicle as larger rectangle
            cv2.rectangle(frame, (x, y), (x+w, y+h), self.color, -1)
            cv2.rectangle(frame, (x+5, y+5), (x+w-5, y+h-5), (50,50,50), 2)
            cv2.putText(frame, "V", (x+10, y+h-10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 2)

def generate_proximity_video():
    """Generate video demonstrating pedestrian-vehicle proximity"""
    print("🎬 Generating proximity alert video...")
    
    width, height = 1280, 720
    fps = 30
    duration = 15  # seconds
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    output = OUTPUT_DIR / "demo_proximity.mp4"
    writer = cv2.VideoWriter(str(output), fourcc, fps, (width, height))
    
    # Create objects
    person = MovingObject(
        "person", 
        [width * 0.2, height * 0.5], 
        [2, 0], 
        (30, 70), 
        (100, 150, 200)
    )
    
    vehicle = MovingObject(
        "vehicle",
        [width * 0.8, height * 0.5],
        [-3, 0],
        (80, 50),
        (50, 100, 150)
    )
    
    for frame_num in range(fps * duration):
        # Create frame (dark gray background like CCTV)
        frame = np.ones((height, width, 3), dtype=np.uint8) * 40
        
        # Add timestamp
        timestamp = f"2026-10-08 14:32:{frame_num//fps:02d}"
        cv2.putText(frame, timestamp, (20, 40),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2)
        
        # Add camera label
        cv2.putText(frame, "CAM-01 | MAIN ENTRANCE", (20, height-20),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (150, 150, 150), 1)
        
        # Update and draw objects
        person.update()
        vehicle.update()
        
        person.draw(frame)
        vehicle.draw(frame)
        
        # Calculate distance
        dist = abs(person.pos[0] - vehicle.pos[0])
        
        # Show distance warning
        if dist < 200:
            alert_text = f"PROXIMITY ALERT: {int(dist)}px"
            cv2.putText(frame, alert_text, (width//2 - 150, 80),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
        
        writer.write(frame)
    
    writer.release()
    print(f"✅ Created: {output}")

def generate_loitering_video():
    """Generate video demonstrating loitering detection"""
    print("🎬 Generating loitering detection video...")
    
    width, height = 1280, 720
    fps = 30
    duration = 20
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    output = OUTPUT_DIR / "demo_loitering.mp4"
    writer = cv2.VideoWriter(str(output), fourcc, fps, (width, height))
    
    # Stationary person with small movements
    person_pos = [width * 0.4, height * 0.5]
    
    for frame_num in range(fps * duration):
        frame = np.ones((height, width, 3), dtype=np.uint8) * 40
        
        timestamp = f"2026-10-08 14:30:{frame_num//fps:02d}"
        cv2.putText(frame, timestamp, (20, 40),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2)
        
        cv2.putText(frame, "CAM-02 | PARKING AREA", (20, height-20),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (150, 150, 150), 1)
        
        # Small random movement (pacing)
        if frame_num % 60 < 30:
            person_pos[0] += 0.5
        else:
            person_pos[0] -= 0.5
        
        # Draw person
        x, y = int(person_pos[0]), int(person_pos[1])
        cv2.rectangle(frame, (x, y), (x+30, y+70), (100, 150, 200), -1)
        cv2.circle(frame, (x+15, y-10), 8, (100, 150, 200), -1)
        
        # Show loitering warning after 10 seconds
        if frame_num > fps * 10:
            duration_text = f"LOITERING DETECTED: {(frame_num//fps) - 10}s"
            cv2.putText(frame, duration_text, (width//2 - 200, 80),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 165, 255), 2)
        
        writer.write(frame)
    
    writer.release()
    print(f"✅ Created: {output}")

def generate_crowd_video():
    """Generate video demonstrating crowd formation"""
    print("🎬 Generating crowd formation video...")
    
    width, height = 1280, 720
    fps = 30
    duration = 15
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    output = OUTPUT_DIR / "demo_crowd.mp4"
    writer = cv2.VideoWriter(str(output), fourcc, fps, (width, height))
    
    # Create multiple people converging
    people = []
    for i in range(15):
        angle = (i / 15) * 2 * np.pi
        start_x = width//2 + 300 * np.cos(angle)
        start_y = height//2 + 200 * np.sin(angle)
        
        vel_x = -2 * np.cos(angle)
        vel_y = -1.5 * np.sin(angle)
        
        person = MovingObject(
            "person",
            [start_x, start_y],
            [vel_x, vel_y],
            (25, 60),
            (80 + i*10, 120, 180)
        )
        people.append(person)
    
    for frame_num in range(fps * duration):
        frame = np.ones((height, width, 3), dtype=np.uint8) * 40
        
        timestamp = f"2026-10-08 14:28:{frame_num//fps:02d}"
        cv2.putText(frame, timestamp, (20, 40),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2)
        
        cv2.putText(frame, "CAM-03 | PLAZA", (20, height-20),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (150, 150, 150), 1)
        
        # Update and draw people
        for person in people:
            person.update()
            person.draw(frame)
        
        # Show crowd warning after people gather
        if frame_num > fps * 8:
            cv2.putText(frame, f"CROWD DETECTED: {len(people)} people", 
                       (width//2 - 180, 80),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 165, 255), 2)
        
        writer.write(frame)
    
    writer.release()
    print(f"✅ Created: {output}")

def generate_perimeter_video():
    """Generate an illustrative restricted-zone entry scenario."""
    width, height, fps = 960, 540, 24
    writer = cv2.VideoWriter(str(OUTPUT_DIR / "demo_perimeter.mp4"), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))
    for frame_num in range(fps * 18):
        frame = np.full((height, width, 3), 38, np.uint8)
        cv2.rectangle(frame, (80, 115), (870, 440), (54, 60, 59), -1)
        cv2.rectangle(frame, (420, 115), (870, 440), (18, 90, 135), 2)
        cv2.putText(frame, "RESTRICTED ZONE", (444, 145), cv2.FONT_HERSHEY_SIMPLEX, .65, (110, 180, 220), 1)
        x = 125 + min(frame_num * 2, 590)
        cv2.circle(frame, (x + 16, 280), 11, (175, 190, 205), -1)
        cv2.line(frame, (x + 16, 292), (x + 16, 355), (205, 215, 220), 7)
        cv2.line(frame, (x + 16, 312), (x, 340), (205, 215, 220), 5)
        cv2.line(frame, (x + 16, 312), (x + 32, 340), (205, 215, 220), 5)
        cv2.rectangle(frame, (x - 12, 265), (x + 45, 364), (100, 220, 160) if x < 420 else (90, 115, 230), 2)
        cv2.putText(frame, "PERSON TRACKED" if x < 420 else "ZONE ENTRY", (28, 38), cv2.FONT_HERSHEY_SIMPLEX, .65, (130, 220, 175) if x < 420 else (115, 155, 245), 2)
        cv2.putText(frame, "CAM-04 | SYNTHETIC SCENARIO", (25, 510), cv2.FONT_HERSHEY_SIMPLEX, .45, (170, 180, 185), 1)
        writer.write(frame)
    writer.release()

def generate_unattended_video():
    """Generate an illustrative unattended-object monitoring scenario."""
    width, height, fps = 960, 540, 24
    writer = cv2.VideoWriter(str(OUTPUT_DIR / "demo_unattended.mp4"), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))
    for frame_num in range(fps * 18):
        frame = np.full((height, width, 3), 42, np.uint8)
        cv2.rectangle(frame, (40, 90), (920, 440), (53, 61, 63), -1)
        cv2.line(frame, (40, 365), (920, 365), (115, 116, 106), 3)
        if frame_num < 100:
            x = 280 + frame_num * 4
            cv2.circle(frame, (x + 12, 275), 9, (190, 200, 205), -1)
            cv2.line(frame, (x + 12, 286), (x + 12, 342), (205, 215, 220), 6)
            cv2.line(frame, (x + 12, 304), (x - 1, 330), (205, 215, 220), 4)
        cv2.rectangle(frame, (510, 340), (553, 367), (76, 115, 165), -1)
        if frame_num >= 100:
            cv2.rectangle(frame, (498, 328), (565, 375), (100, 190, 220), 2)
            cv2.putText(frame, "OBJECT UNDER REVIEW", (28, 38), cv2.FONT_HERSHEY_SIMPLEX, .65, (120, 200, 225), 2)
        cv2.putText(frame, "CAM-05 | SYNTHETIC SCENARIO", (25, 510), cv2.FONT_HERSHEY_SIMPLEX, .45, (170, 180, 185), 1)
        writer.write(frame)
    writer.release()

def main():
    """Generate all demo videos"""
    print("="*80)
    print("CIVIS Demo Video Generator")
    print("="*80)
    
    generate_proximity_video()
    generate_loitering_video()
    generate_crowd_video()
    generate_perimeter_video()
    generate_unattended_video()

    # OpenCV's mp4v output is decodable by CV but often unsupported by browsers.
    # Convert generated examples once to compact H.264 for direct web playback.
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    for source in OUTPUT_DIR.glob("demo_*.mp4"):
        converted = source.with_name(f"{source.stem}.h264.mp4")
        subprocess.run([
            ffmpeg, "-y", "-i", str(source), "-an", "-vf", "scale=w='min(1280,iw)':h=-2",
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "27", "-pix_fmt", "yuv420p",
            "-movflags", "+faststart", str(converted)
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        converted.replace(source)
    
    print("\n" + "="*80)
    print(f"✨ Demo videos created in: {OUTPUT_DIR}")
    print("="*80)
    print("\nGenerated videos:")
    print("  demo_proximity.mp4   - Pedestrian-vehicle proximity (synthetic)")
    print("  demo_loitering.mp4   - Loitering (synthetic)")
    print("  demo_crowd.mp4       - Crowd gathering (synthetic)")
    print("  demo_perimeter.mp4   - Restricted zone entry (synthetic)")
    print("  demo_unattended.mp4  - Unattended object (synthetic)")
    print("\nUse these videos to test the CIVIS system!")

if __name__ == "__main__":
    main()
