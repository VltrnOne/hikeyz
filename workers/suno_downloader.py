#!/usr/bin/env python3
"""
SUNO Downloader Worker for hitbot.agency
Integrates with the SaaS backend API
"""

import time
import os
import re
import json
import requests
import zipfile
from selenium import webdriver
from selenium.webdriver.common.by import By
from datetime import datetime

# Suppress warnings
import warnings
warnings.filterwarnings("ignore")
import urllib3
urllib3.disable_warnings()

class SUNODownloader:
    """Worker class for downloading SUNO songs"""

    def __init__(self, job_id, session_token, credentials, max_songs=20):
        self.job_id = job_id
        self.session_token = session_token
        self.credentials = credentials
        self.max_songs = max_songs
        self.download_dir = f"/Users/Morpheous/vltrndataroom/hitbot-agency/downloads/{job_id}/"
        self.progress = {
            'status': 'pending',
            'total_songs': 0,
            'downloaded': 0,
            'failed': 0,
            'current_song': None,
            'error_message': None
        }

        # Create download directory
        os.makedirs(self.download_dir, exist_ok=True)

    def clean_title(self, title):
        """Clean title for filename"""
        title = re.sub(r'[^\w\s-]', '', title)[:50].strip()
        return title if title else "untitled"

    def extract_song_id(self, url):
        """Extract clean song ID from URL"""
        base_url = url.split('?')[0]
        song_id = base_url.split('/song/')[-1] if '/song/' in base_url else None
        return song_id

    def get_cdn_url(self, song_id):
        """Construct direct CDN URL for song"""
        return f"https://cdn1.suno.ai/{song_id}.mp3"

    def update_progress(self, **kwargs):
        """Update progress and save to file"""
        self.progress.update(kwargs)

        # Save progress to file for API to read
        progress_file = f"/Users/Morpheous/vltrndataroom/hitbot-agency/downloads/{self.job_id}_progress.json"
        with open(progress_file, 'w') as f:
            json.dump(self.progress, f, indent=2)

    def connect_to_chrome(self):
        """Connect to Chrome with debugging port"""
        print("Connecting to Chrome...")
        options = webdriver.ChromeOptions()
        options.add_experimental_option('debuggerAddress', 'localhost:9222')

        try:
            driver = webdriver.Chrome(options=options)
            print(f"Connected! Current page: {driver.current_url}")
            return driver
        except Exception as e:
            raise Exception(f"Failed to connect to Chrome: {e}")

    def load_songs(self, driver):
        """Load and extract song URLs from SUNO profile"""
        print("Navigating to SUNO profile...")

        # Navigate to SUNO
        if 'suno.com/me' not in driver.current_url:
            driver.get('https://suno.com/me')
            time.sleep(5)

        # Count initial songs
        initial_songs = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/song/"]')
        print(f"Initial songs loaded: {len(initial_songs)}")

        # Improved scrolling
        print("Loading more songs...")
        last_count = len(initial_songs)
        no_change_count = 0
        scroll_count = 0
        max_scrolls = 20

        while scroll_count < max_scrolls:
            scroll_count += 1

            # Scroll down
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)

            # Count unique songs
            song_elements = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/song/"]')
            unique_urls = set()
            for elem in song_elements:
                href = elem.get_attribute('href')
                if href:
                    base_href = href.split('?')[0]
                    unique_urls.add(base_href)

            current_count = len(unique_urls)

            if current_count >= self.max_songs:
                print(f"Reached target: {current_count} songs")
                break

            if current_count == last_count:
                no_change_count += 1
                if no_change_count >= 5:
                    print(f"No new songs after 5 scrolls. Total: {current_count}")
                    break
            else:
                no_change_count = 0

            last_count = current_count

        # Extract unique songs
        song_elements = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/song/"]')
        unique_songs = {}

        for elem in song_elements:
            try:
                href = elem.get_attribute('href')
                if not href:
                    continue

                song_id = self.extract_song_id(href)
                if not song_id or song_id in unique_songs:
                    continue

                # Try to get title
                try:
                    parent = elem.find_element(By.XPATH, '..')
                    text = parent.text.strip()
                    title = text.split('\n')[0] if text else f"Song_{song_id[:8]}"
                    title = self.clean_title(title)
                except:
                    title = f"Song_{song_id[:8]}"

                unique_songs[song_id] = {
                    'id': song_id,
                    'title': title,
                    'url': href.split('?')[0],
                    'cdn_url': self.get_cdn_url(song_id)
                }
            except:
                continue

        song_data = list(unique_songs.values())
        print(f"Extracted {len(song_data)} unique songs")

        return song_data

    def download_song(self, song, index, total):
        """Download a single song"""
        song_id = song['id']
        title = song['title']
        cdn_url = song['cdn_url']

        print(f"\nSong {index}/{total}: {title}")
        self.update_progress(current_song=title)

        try:
            # Download from CDN
            response = requests.get(cdn_url, stream=True, timeout=30)

            if response.status_code == 200:
                # Save file
                filename = f"{index:03d}_{title}_{song_id[:8]}.mp3"
                filepath = os.path.join(self.download_dir, filename)

                with open(filepath, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)

                # Verify file
                if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
                    size_mb = os.path.getsize(filepath) / (1024 * 1024)
                    print(f"  ✓ Downloaded: {size_mb:.2f} MB")
                    return True, None
                else:
                    print(f"  ✗ Failed: Empty file")
                    if os.path.exists(filepath):
                        os.remove(filepath)
                    return False, "Empty file"
            else:
                print(f"  ✗ Failed: HTTP {response.status_code}")
                return False, f"HTTP {response.status_code}"

        except Exception as e:
            error_msg = str(e)[:100]
            print(f"  ✗ Error: {error_msg}")
            return False, error_msg

    def create_zip(self):
        """Create ZIP file of all downloaded songs"""
        print("\nCreating ZIP file...")

        zip_filename = f"{self.job_id}_songs.zip"
        zip_path = os.path.join(self.download_dir, zip_filename)

        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(self.download_dir):
                for file in files:
                    if file.endswith('.mp3'):
                        file_path = os.path.join(root, file)
                        arcname = os.path.basename(file)
                        zipf.write(file_path, arcname)

        if os.path.exists(zip_path):
            size_mb = os.path.getsize(zip_path) / (1024 * 1024)
            print(f"ZIP created: {size_mb:.2f} MB")
            return zip_path
        else:
            raise Exception("Failed to create ZIP file")

    def run(self):
        """Main download process"""
        try:
            print("="*50)
            print(f"SUNO DOWNLOADER - Job {self.job_id}")
            print("="*50)

            self.update_progress(status='processing', current_song='Connecting to browser')

            # Connect to Chrome
            driver = self.connect_to_chrome()

            # Load songs
            self.update_progress(current_song='Loading song list')
            song_data = self.load_songs(driver)

            # Limit to max_songs
            song_data = song_data[:self.max_songs]

            self.update_progress(
                total_songs=len(song_data),
                current_song='Starting downloads'
            )

            # Download all songs
            print(f"\n{'='*50}")
            print(f"DOWNLOADING {len(song_data)} SONGS")
            print(f"{'='*50}\n")

            downloaded = 0
            failed = 0

            for i, song in enumerate(song_data, 1):
                success, error = self.download_song(song, i, len(song_data))

                if success:
                    downloaded += 1
                else:
                    failed += 1

                # Update progress
                self.update_progress(
                    downloaded=downloaded,
                    failed=failed
                )

                # Progress report
                if i % 5 == 0:
                    success_rate = (downloaded / i) * 100
                    print(f"\n--- Progress: {downloaded}/{i} ({success_rate:.1f}% success) ---\n")

                # Rate limiting
                time.sleep(1.5)

            # Close browser
            driver.quit()

            # Create ZIP
            self.update_progress(current_song='Creating ZIP file')
            zip_path = self.create_zip()

            # Final summary
            print(f"\n{'='*50}")
            print("DOWNLOAD COMPLETE")
            print(f"{'='*50}")
            print(f"Total songs: {len(song_data)}")
            print(f"Successfully downloaded: {downloaded}")
            print(f"Failed: {failed}")
            print(f"Success rate: {(downloaded/len(song_data)*100):.1f}%")
            print(f"ZIP file: {zip_path}")
            print(f"{'='*50}\n")

            # Update final status
            self.update_progress(
                status='completed',
                current_song=None,
                zip_file_path=zip_path
            )

            return {
                'success': True,
                'total_songs': len(song_data),
                'downloaded': downloaded,
                'failed': failed,
                'zip_path': zip_path
            }

        except Exception as e:
            error_msg = str(e)
            print(f"\nFATAL ERROR: {error_msg}")

            self.update_progress(
                status='failed',
                error_message=error_msg
            )

            return {
                'success': False,
                'error': error_msg
            }

def main():
    """CLI entry point for testing"""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python3 suno_downloader.py <job_id> [max_songs]")
        sys.exit(1)

    job_id = sys.argv[1]
    max_songs = int(sys.argv[2]) if len(sys.argv) > 2 else 20
    session_token = "test_session"
    credentials = {}

    downloader = SUNODownloader(job_id, session_token, credentials, max_songs)
    result = downloader.run()

    print(f"\nResult: {json.dumps(result, indent=2)}")

if __name__ == "__main__":
    main()
